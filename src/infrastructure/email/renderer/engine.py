from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from src.config.settings import Settings
from src.infrastructure.email.models import EmailMessage


@dataclass(slots=True)
class EmailTemplateRenderer:
    base_path: Path
    env: Environment

    @classmethod
    def create_default(cls) -> EmailTemplateRenderer:
        base = Path(__file__).resolve().parent.parent / "templates"
        env = Environment(
            loader=FileSystemLoader(str(base)),
            autoescape=select_autoescape(["html", "xml"]),
            enable_async=False,
        )
        return cls(base_path=base, env=env)

    def _resolve(self, template_key: str, locale: str, name: str) -> str:
        # e.g. es/access_request/subject.txt.j2
        return f"{locale}/{template_key}/{name}"

    def render(
        self,
        *,
        template_key: str,
        settings: Settings,
        context: dict[str, Any],
        locale: str | None = None,
    ) -> EmailMessage:
        loc = (locale or settings.email_default_locale or "es").lower()
        # Merge common variables
        common: dict[str, Any] = {
            "app": {
                "name": settings.email_from_name,
                "primary_color": settings.email_primary_color,
            }
        }
        ctx = {**common, **context}

        def load_template(path: str):
            try:
                return self.env.get_template(path)
            except TemplateNotFound:
                # Fallback to 'es'
                if not path.startswith("es/"):
                    alt = path.replace(f"{loc}/", "es/", 1)
                    return self.env.get_template(alt)
                raise

        subj_tpl = load_template(self._resolve(template_key, loc, "subject.txt.j2"))
        text_tpl = load_template(self._resolve(template_key, loc, "body.txt.j2"))
        html_tpl = None
        try:
            html_tpl = load_template(self._resolve(template_key, loc, "body.html.j2"))
        except TemplateNotFound:
            html_tpl = None

        subject = subj_tpl.render(ctx).strip()
        text = text_tpl.render(ctx).strip()
        html = None
        if html_tpl is not None:
            # Wrap with layout if present
            try:
                layout = load_template(f"{loc}/_layout.html.j2")
            except TemplateNotFound:
                layout = None
            inner = html_tpl.render(ctx)
            html = layout.render({**ctx, "content": inner}) if layout is not None else inner

        return EmailMessage(
            subject=subject,
            to=[],  # caller sets recipients
            text=text,
            html=html,
        )
