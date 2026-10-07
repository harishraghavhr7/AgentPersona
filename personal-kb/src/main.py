import sys
from datetime import datetime, timezone
import logging

from config.settings import get_settings
from ingestion.service import IngestionService
from generation.answer import GenerationService
from evaluation.runner import EvaluationRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def ingest_command():
    print("\n=== STARTING TEMPORAL KNOWLEDGE INGESTION ===")
    service = IngestionService()
    results = service.ingest_directory()
    print("=== INGESTION FINISHED ===")
    print(f"  Processed: {results['processed']}")
    print(f"  Added:     {results['added']}")
    print(f"  Updated:   {results['updated']}")
    print(f"  Skipped:   {results['skipped']}")
    print(f"  Failed:    {results['failed']}")
    print("==========================================\n")


def chat_command():
    gen_service = GenerationService()

    print("\n" + "=" * 60)
    print("Personal Knowledge Base with Temporal Memory (CLI Chat)")
    print("Commands: 'exit' to quit, '/debug' to toggle debug mode.")
    print("=" * 60 + "\n")

    debug_mode = False

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat.")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            print("Goodbye!")
            break

        if user_input.lower() == "/debug":
            debug_mode = not debug_mode
            print(f"[Debug mode: {'ON' if debug_mode else 'OFF'}]\n")
            continue

        response = gen_service.generate_answer(
            query=user_input,
            debug=debug_mode,
        )

        print("\nAssistant:")
        print(response.answer)

        if response.sources:
            print("\nSources:")
            for s in response.sources:
                date_str = f" | Date: {s.event_at}" if s.event_at else ""
                status_str = f" | Status: {s.status}" if s.status else ""
                score_str = f" | Score: {s.score}" if s.score is not None else ""
                print(f"  - [{s.source}]{date_str}{status_str}{score_str}")

        if debug_mode and response.debug_info:
            print("\n[Debug Details]")
            for k, v in response.debug_info.items():
                print(f"  {k}: {v}")

        print("\n" + "-" * 60)


def serve_command():
    import uvicorn
    print("\nStarting FastAPI server on http://localhost:8000 ...")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)


def eval_command():
    runner = EvaluationRunner()
    runner.run_evaluation()


def main():
    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  python src/main.py ingest   - Run incremental temporal ingestion\n"
            "  python src/main.py chat     - Interactive terminal chat\n"
            "  python src/main.py serve    - Start the FastAPI REST service\n"
            "  python src/main.py eval     - Run evaluation benchmark scorecard\n"
        )
        return

    command = sys.argv[1].lower()

    if command == "ingest":
        ingest_command()
    elif command == "chat":
        chat_command()
    elif command == "serve":
        serve_command()
    elif command == "eval":
        eval_command()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: ingest, chat, serve, eval")


if __name__ == "__main__":
    main()