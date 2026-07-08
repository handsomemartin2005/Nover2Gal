from __future__ import annotations

import argparse
from pathlib import Path

from app.exporters.json_exporter import export_project_to_json
from app.importers.document_importer import import_document
from app.services.novel_pipeline import run_pipeline


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Novel2Gal backend MVP pipeline.")
    parser.add_argument("input", help="Path to txt/md novel input")
    parser.add_argument("--title", help="Novel title; defaults to imported document title")
    parser.add_argument("--pov", required=True, help="POV character name")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_dir = Path(args.out)
    document = import_document(input_path)
    title = args.title or document.title
    result = run_pipeline(title, document.text, args.pov)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "script.md").write_text(result.exports["markdown"], encoding="utf-8")
    (output_dir / "project.json").write_text(export_project_to_json(result), encoding="utf-8")
    game_dir = output_dir / "game"
    game_dir.mkdir(parents=True, exist_ok=True)
    (game_dir / "script.rpy").write_text(result.exports["renpy"], encoding="utf-8")
    return 0


def main() -> None:
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()
