import os
import sys
import time
import json
import oqs
import base64
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, IntPrompt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Import existing logic
from verify import detect_bank
from bank_registry import MultiBankGateway

console = Console()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_header():
    console.print(Panel.fit(
        "[bold cyan]TRINEX: Secure Financial Communication System[/bold cyan]\n"
        "[bold white]Phase 2: Full PQC Synchronization Demo[/bold white]\n"
        "[dim]Authenticity: ML-DSA-65 (Dilithium) | Secrecy: ML-KEM-768 (Kyber)[/dim]",
        border_style="blue"
    ))

def aes_encrypt(key, plaintext):
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
    return base64.b64encode(iv + ciphertext).decode()

def aes_decrypt(key, b64_ciphertext):
    raw = base64.b64decode(b64_ciphertext)
    iv = raw[:16]
    ciphertext = raw[16:]
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    return (decryptor.update(ciphertext) + decryptor.finalize()).decode()

def run_demo():
    # 1. Initialize Gateway
    with console.status("[bold green]Loading PQC Bank Registry...") as status:
        gateway = MultiBankGateway()
        time.sleep(1.5)

    while True:
        clear_screen()
        show_header()
        
        # --- STEP 1: BANK SELECTION ---
        console.print("\n[bold yellow]Step 1: Select Bank for Transaction[/bold yellow]")
        bank_list = list(gateway.banks.keys())[:10]
        table = Table(title="Bank Registry", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Bank Name", style="white")
        table.add_column("Type", style="dim")
        
        for i, b in enumerate(bank_list):
            bank_info = gateway.banks[b]['info']
            table.add_row(str(i+1), bank_info['name'], bank_info['type'])
        console.print(table)
        
        choice = IntPrompt.ask("[bold white]Select Bank ID to initiate handshake[/bold white]", choices=[str(i+1) for i in range(len(bank_list))])
        selected_bank = bank_list[choice-1]
        sender_id = gateway.banks[selected_bank]['sender_ids'][0]
        bank_signer = gateway.banks[selected_bank]['signer']

        # --- STEP 2: QUANTUM HANDSHAKE (KYBER) ---
        clear_screen()
        show_header()
        console.print(f"\n[bold yellow]Step 2: PQC Handshake (Kyber-768)[/bold yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            # Client Side: Generate Kyber Keypair
            progress.add_task(description="[cyan]Receiver generating ML-KEM-768 keypair...", total=None)
            with oqs.KeyEncapsulation("ML-KEM-768") as client_kem:
                client_pub = client_kem.generate_keypair()
                time.sleep(0.8)
                
                # Bank Side: Encapsulate
                progress.add_task(description="[blue]Bank encapsulating shared secret...", total=None)
                with oqs.KeyEncapsulation("ML-KEM-768") as bank_kem:
                    ciphertext, shared_secret = bank_kem.encap_secret(client_pub)
                    time.sleep(0.8)
                    
                    # Bank Side: Sign the Handshake with Dilithium
                    progress.add_task(description="[magenta]Bank signing handshake with ML-DSA-65...", total=None)
                    handshake_sig = bank_signer.sign(ciphertext)
                    time.sleep(0.6)

            # Verification at Client
            is_handshake_valid = bank_signer.verify(ciphertext, handshake_sig, gateway.public_keys[selected_bank])
            
        if is_handshake_valid:
            console.print(Panel(
                f"[bold green]✅ Handshake Verified[/bold green]\n"
                f"[white]Identity confirmed for:[/white] [cyan]{gateway.banks[selected_bank]['info']['name']}[/cyan]\n"
                f"[white]Established AES-256 Key:[/white] [dim]{shared_secret.hex()[:32]}...[/dim]",
                title="Secure Channel Established", border_style="green"
            ))
        else:
            console.print("[bold red]❌ Handshake Failed![/bold red] Potential Man-in-the-middle detected.")
            break

        # --- STEP 3: ENCRYPTED COMMUNICATION ---
        console.print(f"\n[bold yellow]Step 3: Secure Message Creation[/bold yellow]")
        msg_text = Prompt.ask("Enter message to encrypt", default=f"Your secret OTP is {os.urandom(3).hex().upper()}")
        
        with console.status("[bold blue]Encrypting with AES-256 + Signing with ML-DSA...") as status:
            encrypted_msg = aes_encrypt(shared_secret, msg_text)
            final_sig = bank_signer.sign(encrypted_msg.encode())
            time.sleep(1)
            
        console.print(Panel(
            f"[white]Encrypted Payload:[/white] [cyan]{encrypted_msg}[/cyan]\n"
            f"[white]PQC Signature:[/white]   [dim]{final_sig.hex()[:64]}...[/dim]",
            title="Outgoing Quantum-Safe Packet", border_style="cyan"
        ))

        # --- STEP 4: VERIFICATION & DECRYPTION ---
        console.print(f"\n[bold yellow]Step 4: Receiver Verification & Security Audit[/bold yellow]")
        
        attack = Prompt.ask("Apply attack scenario?", choices=["None", "Tamper", "Wrong-Key"], default="None")
        
        test_body = encrypted_msg
        test_secret = shared_secret

        if attack == "Tamper":
            # Modify the base64 ciphertext (change a few characters)
            chars = list(encrypted_msg)
            chars[-5:] = "ABCDE"
            test_body = "".join(chars)
            console.print("[bold red]🔥 ATTACK:[/bold red] Ciphertext modified in transit. Signature should fail.")
        
        elif attack == "Wrong-Key":
            test_secret = os.urandom(32) # Complete mismatch
            console.print("[bold red]🔥 ATTACK:[/bold red] Attacker attempting unauthorized decryption with a rogue key.")

        # 1. Verify Authenticity (Signature)
        valid_sig = bank_signer.verify(test_body.encode(), final_sig, gateway.public_keys[selected_bank])
        
        if not valid_sig:
            console.print(Panel(
                "[bold red]❌ SECURITY ALERT: TAMPERING DETECTED[/bold red]\n"
                "The ML-DSA-65 signature does not match the payload. The packet has been rejected.", 
                title="Integrity Failure", border_style="red"
            ))
        else:
            # 2. Attempt Decryption
            try:
                decrypted = aes_decrypt(test_secret, test_body)
                
                # Double check the 'attack' variable value here for robust branching
                if attack == "Wrong-Key":
                    console.print(Panel(
                        f"[bold yellow]⚠️ CRYPTOGRAPHIC FAILURE[/bold yellow]\n"
                        f"[white]Key Mismatch:[/white] Decryption succeeded but key was unauthorized.\n"
                        f"[white]Resulting Garbage:[/white] [dim]{decrypted}[/dim]",
                        title="Secrecy Violation Detected", border_style="yellow"
                    ))
                else:
                    console.print(Panel(
                        f"[bold green]✅ Message Authenticated & Decrypted[/bold green]\n"
                        f"[white]From:[/white] {gateway.banks[selected_bank]['info']['name']}\n"
                        f"[white]Content:[/white] [bold white]{decrypted}[/bold white]",
                        title="Secure Communication Success", border_style="green"
                    ))
            except Exception as e:
                # If decryption fails (e.g. padding error if we used padded mode, but CFB usually just returns garbage)
                # or if decoding fails (most likely case for wrong key in CFB)
                console.print(Panel(
                    f"[bold red]❌ DECRYPTION ERROR[/bold red]\n"
                    f"Cryptographic failure during processing: {str(e)}\n"
                    f"This usually indicates an incorrect decryption key.", 
                    title="Secrecy Failure", border_style="red"
                ))

        if not Prompt.ask("\nRun another scenario?", choices=["y", "n"], default="y") == "y":
            break

    console.print("\n[bold cyan]Full PQC Synchronization Demo Concluded.[/bold cyan]")

if __name__ == "__main__":
    try:
        run_demo()
    except Exception as e:
        console.print(f"[bold red]System Error:[/bold red] {e}")
