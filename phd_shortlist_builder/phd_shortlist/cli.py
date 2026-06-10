from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from phd_shortlist.builder import ShortlistBuilder
from phd_shortlist.config import RuntimeConfig
from phd_shortlist.io import read_student_profile, write_json_model
from phd_shortlist.outcomes import load_outcome_signals
from phd_shortlist.validate import validate_shortlist

app = typer.Typer(help="Build and validate PhD supervisor shortlists.")
console = Console()


@app.command()
def build(
    profile: Path = typer.Argument(..., help="Path to student profile JSON"),
    output: Path = typer.Option(Path("sample_output/shortlist.json"), "--output", "-o"),
    min_recommendations: int = typer.Option(50, "--min"),
    max_recommendations: int = typer.Option(200, "--max"),
    per_area_candidate_limit: int = typer.Option(80, "--per-area"),
    outcomes_csv: Path | None = typer.Option(None, "--outcomes-csv"),
    cache_dir: Path = typer.Option(Path(".cache/phd_shortlist"), "--cache-dir"),
    openalex_mailto: str | None = typer.Option(None, "--openalex-mailto"),
    offline: bool = typer.Option(False, "--offline", help="Use cache only; no network requests."),
    insecure_skip_tls_verify: bool = typer.Option(
        False,
        "--insecure-skip-tls-verify",
        help="Disable TLS verification only for restricted proxy environments.",
    ),
) -> None:
    """Generate a machine-readable supervisor shortlist."""
    student = read_student_profile(profile)
    config = RuntimeConfig(
        min_recommendations=min_recommendations,
        max_recommendations=max_recommendations,
        per_area_candidate_limit=per_area_candidate_limit,
        cache_dir=cache_dir,
        openalex_mailto=openalex_mailto,
        offline=offline,
        insecure_skip_tls_verify=insecure_skip_tls_verify,
    )
    signals = load_outcome_signals(outcomes_csv)
    shortlist = ShortlistBuilder(config, signals).build(student)
    write_json_model(shortlist, output)
    errors = validate_shortlist(shortlist)
    if errors:
        console.print(f"[yellow]Wrote {output} with {len(errors)} validation warnings.[/yellow]")
        for error in errors[:10]:
            console.print(f"  - {error}")
    else:
        console.print(f"[green]Wrote validated shortlist to {output}[/green]")


@app.command()
def validate(path: Path = typer.Argument(..., help="Path to shortlist JSON")) -> None:
    """Validate a generated shortlist JSON."""
    from phd_shortlist.io import read_json
    from phd_shortlist.models.schema import ShortlistOutput

    output = ShortlistOutput.model_validate(read_json(path))
    errors = validate_shortlist(output)
    if errors:
        for error in errors:
            console.print(f"[red]- {error}[/red]")
        raise typer.Exit(code=1)
    console.print("[green]Shortlist schema and hard constraints validated.[/green]")


if __name__ == "__main__":
    app()
