# Reference

## Environment Checks

Run these checks in the interpreter that will execute the conversion:

```bash
python -c "import sys; print(sys.executable)"
python -m pip show marker-pdf
python -c "import marker, pydantic, pdftext, surya, cv2"
```

If those commands use different environments than expected, fix the interpreter mismatch before debugging `marker` itself.

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
