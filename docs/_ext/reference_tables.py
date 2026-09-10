"""Render reference tables directly from the parser's product and variable metadata."""

from docutils import nodes
from docutils.parsers.rst import Directive

from xndbc._products import MODES
from xndbc._variables import VARIABLES


class ReferenceTable(Directive):
    required_arguments = 1

    def run(self):
        if self.arguments[0] == "products":
            headers = ["Mode", "Description", "Historical", "Realtime"]
            rows = [
                (name, item.description, "Yes" if item.historical else "No",
                 "Yes" if item.realtime_extension else "No")
                for name, item in MODES.items()
            ]
        elif self.arguments[0] == "variables":
            headers = ["Variable", "Description", "Units", "Numeric missing code"]
            rows = [
                (name, item.long_name, item.units,
                 "None" if item.missing_value is None else str(item.missing_value))
                for name, item in VARIABLES.items()
            ]
        else:
            raise self.error("Expected 'products' or 'variables'.")
        table = nodes.table()
        group = nodes.tgroup(cols=len(headers))
        table += group
        for _ in headers:
            group += nodes.colspec(colwidth=1)
        head, body = nodes.thead(), nodes.tbody()
        group += head
        group += body
        for parent, values in [(head, headers), *((body, row) for row in rows)]:
            row = nodes.row()
            for value in values:
                entry = nodes.entry()
                entry += nodes.paragraph(text=value)
                row += entry
            parent += row
        # Metadata changes also invalidate an incremental Sphinx build.
        import xndbc._products
        import xndbc._variables

        for module in (xndbc._products, xndbc._variables):
            self.state.document.settings.env.note_dependency(module.__file__)
        return [table]


def setup(app):
    app.add_directive("ndbc-reference", ReferenceTable)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
