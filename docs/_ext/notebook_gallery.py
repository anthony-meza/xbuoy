"""List runnable notebook downloads without making notebooks website chapters."""

import json
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList


class NotebookGallery(Directive):
    def run(self):
        env = self.state.document.settings.env
        directory = Path(env.srcdir) / "examples"
        env.note_dependency(str(directory))
        lines = []
        paths = sorted(directory.glob("*.ipynb"), key=lambda p: (p.stem != "getting_started", p.name))
        for path in paths:
            env.note_dependency(str(path))
            notebook = json.loads(path.read_text())
            intro = next(cell for cell in notebook["cells"] if cell["cell_type"] == "markdown")
            paragraphs = "".join(intro["source"]).strip().split("\n\n")
            title = paragraphs[0].lstrip("# ").replace("\n", " ")
            description = paragraphs[1].replace("\n", " ") if len(paragraphs) > 1 else ""
            lines.extend([
                f"* :download:`{title} </examples/{path.name}>`",
                "",
                f"  {description}",
                "",
            ])
        result = nodes.container()
        self.state.nested_parse(StringList(lines), self.content_offset, result)
        return [result]


def setup(app):
    app.add_directive("notebook-gallery", NotebookGallery)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
