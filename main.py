"""Chat de Hir.ia en la terminal.  Uso:  python main.py   (escribe 'salir' para terminar)"""
from dotenv import load_dotenv

load_dotenv()  # lee ANTHROPIC_API_KEY y HIRIA_MODELO de .env

from hiria.agente import agente  # noqa: E402


def main():
    historial = []
    print("Hir.ia · escribe 'salir' para terminar\n")
    while True:
        try:
            msg = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in ("salir", "exit", "quit"):
            break
        if not msg:
            continue
        r = agente.run_sync(msg, message_history=historial)
        historial = r.all_messages()
        print(f"\n{r.output}\n")


if __name__ == "__main__":
    main()
