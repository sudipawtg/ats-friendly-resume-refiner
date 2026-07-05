import logging
import os
import shutil
import subprocess
from pathlib import Path

from app.config import Settings

logger = logging.getLogger(__name__)


class LatexCompileError(Exception):
    pass


class LatexCompileService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def compile_output_to_pdf(self, output_dir: Path, master_file: str) -> Path:
        output_dir = output_dir.resolve()
        main_tex = (output_dir / master_file).resolve()
        if not main_tex.exists():
            raise FileNotFoundError(f"Main TeX file not found: {main_tex}")

        search_paths = self._collect_search_paths(output_dir, main_tex)
        compiler = self._find_compiler()
        if compiler == "tectonic":
            return self._compile_with_tectonic(output_dir, main_tex, search_paths)
        if compiler == "pdflatex":
            return self._compile_with_pdflatex(output_dir, main_tex, search_paths)
        raise LatexCompileError(
            "No LaTeX compiler found. Install tectonic (`brew install tectonic`) "
            "or a TeX distribution with pdflatex."
        )

    def _collect_search_paths(self, output_dir: Path, main_tex: Path) -> list[Path]:
        candidates = [output_dir.resolve(), main_tex.parent.resolve()]
        unique_paths: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate)
            if key not in seen:
                seen.add(key)
                unique_paths.append(candidate)
        return unique_paths

    def _build_texinputs(self, search_paths: list[Path]) -> str:
        path_prefix = ":".join(f"{path}//" for path in search_paths)
        existing = os.environ.get("TEXINPUTS", "")
        return f"{path_prefix}:{existing}" if existing else path_prefix

    def _resolve_pdf_path(self, output_dir: Path, main_tex: Path) -> Path | None:
        candidates = [
            output_dir / f"{main_tex.stem}.pdf",
            main_tex.with_suffix(".pdf"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        for pdf_path in sorted(output_dir.rglob(f"{main_tex.stem}.pdf")):
            if "archive" not in pdf_path.parts:
                return pdf_path
        return None

    def _find_compiler(self) -> str | None:
        if shutil.which("tectonic"):
            return "tectonic"
        if shutil.which("pdflatex"):
            return "pdflatex"
        return None

    def _compile_with_tectonic(
        self, output_dir: Path, main_tex: Path, search_paths: list[Path]
    ) -> Path:
        command = [
            "tectonic",
            "--keep-logs",
            "--outdir",
            str(output_dir.resolve()),
        ]
        for search_path in search_paths:
            command.extend(["-Z", f"search-path={search_path.resolve()}"])
        command.append(str(main_tex.resolve()))

        result = subprocess.run(
            command,
            cwd=str(output_dir),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        pdf_path = self._resolve_pdf_path(output_dir, main_tex)
        if result.returncode != 0 or pdf_path is None:
            log_tail = (result.stderr or result.stdout or "")[-2000:]
            raise LatexCompileError(f"Tectonic compilation failed:\n{log_tail}")
        logger.info("Compiled LaTeX PDF with tectonic: %s", pdf_path)
        return pdf_path

    def _compile_with_pdflatex(
        self, output_dir: Path, main_tex: Path, search_paths: list[Path]
    ) -> Path:
        env = os.environ.copy()
        env["TEXINPUTS"] = self._build_texinputs(search_paths)
        command = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory",
            str(output_dir),
            str(main_tex),
        ]
        for pass_index in range(2):
            result = subprocess.run(
                command,
                cwd=str(output_dir),
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
                env=env,
            )
            if result.returncode != 0:
                log_tail = (result.stderr or result.stdout or "")[-2000:]
                raise LatexCompileError(
                    f"pdflatex pass {pass_index + 1} failed:\n{log_tail}"
                )

        pdf_path = self._resolve_pdf_path(output_dir, main_tex)
        if pdf_path is None:
            raise LatexCompileError("pdflatex completed but PDF was not created")
        logger.info("Compiled LaTeX PDF with pdflatex: %s", pdf_path)
        return pdf_path
