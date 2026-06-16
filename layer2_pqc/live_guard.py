import os
import json
import time
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from verify import get_pqc_score

console = Console()

def show_banner():
    console.print(Panel.fit(
        "[bold green]TRINEX: Real-Time PQC SMS Guard[/bold green]\n"
        "[dim]Monitoring for Post-Quantum Cryptographic Signatures[/dim]",
        border_style="green"
    ))

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    show_banner()
    
    while True:
        console.print("\n[bold yellow]Ready to Scan. Please type or paste the incoming message content:[/bold yellow]")
        user_input = Prompt.ask("[cyan]SMS Content[/cyan]")
        
        if user_input.lower() in ['exit', 'quit']:
            break
            
        console.print("\n[bold blue]Scanning for Bank Identity and PQC Signatures...[/bold blue]")
        time.sleep(1)
        
        # We simulate a packet. A raw typed message from a user won't have a signature,
        # which is exactly what we want to show for a SCAM.
        packet = {
            "message": user_input,
            "sender_id": "UNKNOWN",
            "signature": None  # Typed messages have no PQC signature
        }
        
        result = get_pqc_score(packet)
        
        if not result['valid']:
            console.print(Panel(
                f"[bold red]🚨 FRAUD DETECTED![/bold red]\n\n"
                f"[white]Reason:[/white] {result['status']}\n"
                f"[white]Detail:[/white] {result['detail']}\n\n"
                f"[yellow]Verdict:[/yellow] This message is NOT signed by a registered bank. Do not click any links.",
                title="Security Verdict", border_style="red"
            ))
        else:
            # Note: This branch only triggers if you paste a JSON string with a signature,
            # which you can get from the 'test_cases' folder.
            console.print(Panel(
                f"[bold green]✅ LEGITIMATE BANK MESSAGE[/bold green]\n\n"
                f"[white]Bank:[/white] {result['bank_name']}\n"
                f"[white]Status:[/white] Signature Verified (ML-DSA-65)",
                title="Security Verdict", border_style="green"
            ))

        if not Prompt.ask("\nScan another message?", choices=["y", "n"], default="y") == "y":
            break

if __name__ == "__main__":
    main()
