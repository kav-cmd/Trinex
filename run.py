#!/usr/bin/env python3
"""
TRINEX — master entrypoint.

  python run.py demo          → run the 3-sample pipeline demo
  python run.py analyze       → analyze a single packet (interactive)
  python run.py dashboard     → open the HTML dashboard in your browser
  python run.py serve         → start a tiny HTTP server for the dashboard
                                (useful if file:// fonts get blocked)

The dashboard is fully self-contained — it doesn't need this script
once you've opened it.
"""
import os
import sys
import json
import webbrowser
import http.server
import socketserver

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "fusion_engine"))


def cmd_demo():
    from trinex_pipeline import analyze        # type: ignore
    
    sbi_sig = "a" * 6618
    try:
        from bank_registry import MultiBankGateway
        gateway = MultiBankGateway()
        legit_pkt = gateway.sign_message(
            "Dear Customer, INR 1,500.00 has been debited from A/c XX1234 on 14-Jun-26. Avl Bal: INR 24,300.00.",
            "SBI-ALERTS"
        )
        sbi_sig = legit_pkt['signature']
    except Exception:
        pass

    samples = [
        ("Legitimate SBI alert",
         "Dear Customer, INR 1,500.00 has been debited from A/c XX1234 on "
         "14-Jun-26. Avl Bal: INR 24,300.00.",
         "SBI-ALERTS", sbi_sig, "sbi_tower_profile", "legitimate"),
        ("Phishing — spoofed sender",
         "URGENT: Your SBI account is BLOCKED. Update KYC at http://bit.ly/sbi-kyc "
         "or share OTP to reactivate.",
         "VK-SBIBNK", None, "sbi_tower_profile", "rogue"),
        ("Suspicious — bank header, OTP request",
         "HDFC Bank: Confirm your transaction by sharing the OTP within 5 minutes.",
         "HDFCBK", None, "hdfc_tower_profile", "legitimate"),
    ]
    for label, msg, sid, sig, tower, scenario in samples:
        print("\n" + "═" * 72)
        print(f" {label}")
        print("─" * 72)
        out = analyze(msg, sender_id=sid, signature=sig,
                      claimed_tower=tower, scenario_type=scenario)
        print(f"  Trust Score : {out['trust_score']:.2f}  /  100")
        print(f"  Verdict     : {out['band']}")
        print(f"  Latency     : {out['total_latency_ms']:.1f} ms")
        for layer in out["layers"]:
            avail = "real" if layer["available"] else "heuristic"
            print(f"    {layer['name']:7}  trust={layer['trust']:.3f}  "
                  f"latency={layer['latency_ms']:.1f}ms  [{avail}]")


def cmd_analyze():
    from trinex_pipeline import analyze        # type: ignore
    msg    = input("Message body              > ").strip()
    sid    = input("Sender ID (e.g. SBI-ALERTS)> ").strip() or "UNKNOWN"
    signed = input("Has signature? [y/N]      > ").strip().lower().startswith("y")
    
    signature = None
    if signed:
        try:
            from bank_registry import MultiBankGateway
            gateway = MultiBankGateway()
            signed_pkt = gateway.sign_message(msg, sid)
            signature = signed_pkt['signature']
            print(f"Generated ML-DSA-65 Signature: {signature[:32]}... ({len(signature)//2} bytes)")
        except Exception as e:
            print(f"Failed to generate real signature: {e}. Using dummy signature.")
            signature = "a" * 6618

    out = analyze(msg, sender_id=sid, signature=signature)
    print(json.dumps(out, indent=2))


def cmd_dashboard():
    path = os.path.join(ROOT, "dashboard", "index.html")
    webbrowser.open("file://" + path)


class TrinexRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/analyze":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                message = data.get("message", "")
                sender_id = data.get("sender_id", "UNKNOWN")
                scenario_type = data.get("scenario_type", "legitimate")
                signature = data.get("signature")
                
                # Dynamic signature generation for registered banks if requested
                if data.get("signed") and not signature:
                    try:
                        from bank_registry import MultiBankGateway
                        gateway = MultiBankGateway()
                        signed_pkt = gateway.sign_message(message, sender_id)
                        signature = signed_pkt['signature']
                    except Exception:
                        signature = "a" * 6618

                # Call real trinex_pipeline analysis
                from trinex_pipeline import analyze  # type: ignore
                result = analyze(
                    message=message,
                    sender_id=sender_id,
                    signature=signature,
                    claimed_tower="sbi_tower_profile",
                    scenario_type=scenario_type
                )
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            super().do_POST()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def cmd_serve():
    os.chdir(os.path.join(ROOT, "dashboard"))
    port = 8765
    with socketserver.TCPServer(("", port), TrinexRequestHandler) as httpd:
        url = f"http://localhost:{port}/index.html"
        print(f"TRINEX dashboard serving at {url}")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down.")


COMMANDS = {
    "demo":      cmd_demo,
    "analyze":   cmd_analyze,
    "dashboard": cmd_dashboard,
    "serve":     cmd_serve,
}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(0)
    COMMANDS[sys.argv[1]]()
