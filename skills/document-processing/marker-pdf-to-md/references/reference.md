# Reference

## Environment & Config

Before running any conversion, resolve the Python interpreter via config file:

1. Read `.agent/config/marker-pdf-env.json` to get the known-good Python path.
2. Validate with `{python} -c "import marker, pydantic, pdftext, surya, cv2"`.
3. If config is missing or validation fails, detect and re-save.

### Bash snippet (detect + save)

```bash
# Read existing config (if any)
CONFIG_FILE=".agent/config/marker-pdf-env.json"
PYTHON=""

if [ -f "$CONFIG_FILE" ]; then
    PYTHON=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['python'])" 2>/dev/null)
fi

# Detect if config not found or validation failed
if [ -z "$PYTHON" ] || ! $PYTHON -c "import marker, pydantic, pdftext, surya, cv2" 2>/dev/null; then
    echo "Config missing or invalid — detecting environment..."
    PYTHON=$(python3 -c "import sys; print(sys.executable)")
    IMPORT_OK=$($PYTHON -c "import marker, pydantic, pdftext, surya, cv2; print('OK')" 2>&1)
    if [ "$IMPORT_OK" != "OK" ]; then
        echo "ERROR: marker-pdf not available in $PYTHON" >&2
        echo "Install with: $PYTHON -m pip install marker-pdf" >&2
        exit 1
    fi
    VERSION=$($PYTHON -m pip show marker-pdf 2>/dev/null | grep Version | awk '{print $2}')
    mkdir -p "$(dirname "$CONFIG_FILE")"
    cat > "$CONFIG_FILE" <<EOF
{
  "python": "${PYTHON}",
  "marker_version": "${VERSION}",
  "verified_imports": ["marker", "pydantic", "pdftext", "surya", "cv2"],
  "verified_on": "$(date +%Y-%m-%d)"
}
EOF
    echo "Config saved to $CONFIG_FILE"
fi

echo "Using: $PYTHON"
```

### Python snippet (load config in conversion scripts)

```python
import json, os, subprocess, sys

CONFIG_FILE = ".agent/config/marker-pdf-env.json"

def resolve_python():
    """Return path to known-good Python, detecting + saving if needed."""
    # Try existing config
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        py = cfg["python"]
        try:
            subprocess.run([py, "-c", "import marker, pydantic, pdftext, surya, cv2"],
                           check=True, capture_output=True)
            return py
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    # Detect from current interpreter
    py = sys.executable
    subprocess.run([py, "-c", "import marker, pydantic, pdftext, surya, cv2"],
                   check=True)
    version = subprocess.run([py, "-m", "pip", "show", "marker-pdf"],
                             capture_output=True, text=True)
    ver_line = [l for l in version.stdout.splitlines() if l.startswith("Version:")]
    ver = ver_line[0].split()[-1] if ver_line else "unknown"

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "python": py,
            "marker_version": ver,
            "verified_imports": ["marker", "pydantic", "pdftext", "surya", "cv2"],
            "verified_on": __import__("datetime").date.today().isoformat(),
        }, f, indent=2)
    return py

PYTHON = resolve_python()
```

## In-Memory Conversion

Use this when the user wants the markdown content in memory first and does not care yet about saving files:

```python
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

pdf_path = "reference/Time Interleaving DAC (TI-DAC).pdf"

converter = PdfConverter(
    artifact_dict=create_model_dict(),
)
rendered = converter(pdf_path)
markdown_text, ext, images = text_from_rendered(rendered)

assert ext == "md"
metadata = rendered.metadata
```

`markdown_text` is the Markdown body, `images` is a dict of extracted PIL images, and `rendered.metadata` is what later becomes `_meta.json`.

## Save a Whole PDF to Markdown

Use this when the user wants the standard output folder structure and on-disk artifacts:

```python
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import save_output

pdf_path = "reference/Time Interleaving DAC (TI-DAC).pdf"
config_parser = ConfigParser(
    {
        "output_format": "markdown",
        "output_dir": "reference/output/full_document",
    }
)

converter = PdfConverter(
    config=config_parser.generate_config_dict(),
    artifact_dict=create_model_dict(),
    processor_list=config_parser.get_processors(),
    renderer=config_parser.get_renderer(),
    llm_service=config_parser.get_llm_service(),
)

rendered = converter(pdf_path)
out_folder = config_parser.get_output_folder(pdf_path)
save_output(rendered, out_folder, config_parser.get_base_filename(pdf_path))
```

This writes:

- `<output_dir>/<pdf-base>/<pdf-base>.md`
- `<output_dir>/<pdf-base>/<pdf-base>_meta.json`
- extracted images beside the markdown

## Save a Page Range or Section

Use this when the user knows the page span for the target section. `marker` uses zero-based page indexing in the config layer, so pages `75~78` become `74-77`.

```python
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import save_output

pdf_path = "reference/Time Interleaving DAC (TI-DAC).pdf"
config_parser = ConfigParser(
    {
        "output_format": "markdown",
        "output_dir": "reference/output/section_4_3_1_general_model",
        "page_range": "74-77",
    }
)

converter = PdfConverter(
    config=config_parser.generate_config_dict(),
    artifact_dict=create_model_dict(),
    processor_list=config_parser.get_processors(),
    renderer=config_parser.get_renderer(),
    llm_service=config_parser.get_llm_service(),
)

rendered = converter(pdf_path)
out_folder = config_parser.get_output_folder(pdf_path)
save_output(rendered, out_folder, config_parser.get_base_filename(pdf_path))
```

## Handling Metadata

`save_output()` writes `_meta.json` automatically. That metadata is useful for:

- detected table of contents entries
- page-level extraction statistics
- text extraction method (for example `surya`)
- debug-data paths

If the user only wants the readable result, return the `.md` path first and mention `_meta.json` as optional.

## LLM Guidance

- Default to non-LLM conversion.
- Only discuss local Ollama when the user explicitly asks for higher-quality recovery.
- Local models must support `vision` to work with `marker`'s image-based LLM path.
