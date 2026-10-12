"""The interface's icons, as inline SVG: {{ icon("close") }} or
{{ icon("sun", "icon-sun") }} in any template. Inline, they take the text
color and cost no request; drawn here rather than by a Jinja macro because
a page draws dozens and a macro call costs far more than a lookup.
"""

from markupsafe import Markup, escape

PATHS = {
    "about": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.6v.1"/>',
    "account": '<circle cx="12" cy="8.5" r="3.8"/><path d="M4.5 20c.9-3.6 4-5.5 7.5-5.5s6.6 1.9 7.5 5.5"/>',
    "admin": '<path d="M12 22s8-4 8-10V5.5L12 2.5 4 5.5V12c0 6 8 10 8 10Z"/><path d="m8.8 12 2.2 2.2 4.2-4.4"/>',
    "all": '<path d="M4 5.5h16M4 12h16M4 18.5h10"/>',
    "back": '<path d="M15 5l-7 7 7 7"/>',
    "cards": '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
    "chevron-down": '<path d="m7 10 5 5 5-5"/>',
    "chevron-right": '<path d="m9 5 7 7-7 7"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "delete": '<path d="M5.5 7.5h13M9.5 7V5h5v2M7 7.5l.8 12a1 1 0 0 0 1 .9h6.4a1 1 0 0 0 1-.9l.8-12M10.2 11v6M13.8 11v6"/>',
    "done": '<circle cx="12" cy="12" r="8.5"/><path d="m8.2 12.4 2.6 2.6 5-5.6"/>',
    "edit": '<path d="M4 20h4L19.5 8.5a2 2 0 0 0-3-3L5 17v3ZM13.5 6.5l3 3"/>',
    "key": '<circle cx="7.5" cy="15.5" r="4"/><path d="M10.3 12.7 21 2M15 5l3 3M18 2l3 3"/>',
    "link": '<path d="M10.5 13.5a4 4 0 0 0 6 .4l2.6-2.6a4 4 0 1 0-5.7-5.7l-1.3 1.3M13.5 10.5a4 4 0 0 0-6-.4l-2.6 2.6a4 4 0 1 0 5.7 5.7l1.3-1.3"/>',
    "list": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "loading": '<path d="M20 12a8 8 0 1 1-2.3-5.6"/>',
    "menu": '<path d="M4 6.5h16M4 12h16M4 17.5h16"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z"/>',
    "next": '<path d="M9 5l7 7-7 7"/>',
    "open": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none"/>',
    "pin": '<path d="M7 4.5h10a1 1 0 0 1 1 1V20l-6-3.5L6 20V5.5a1 1 0 0 1 1-1Z"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "refresh": '<path d="M20 12a8 8 0 1 1-2.3-5.6M20 3.5V7h-3.5"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
    "security": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8.5 10.5V7.5a3.5 3.5 0 0 1 7 0v3M12 14.5v2.5"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/>',
    "shield": '<path d="M12 22s8-4 8-10V5.5L12 2.5 4 5.5V12c0 6 8 10 8 10Z"/>',
    "sign-out": '<path d="M14 5H7a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h7M17 15.5 20.5 12 17 8.5M20 12H10"/>',
    "sort": '<path d="M7 4v16M3.5 16.5 7 20l3.5-3.5M14 6h7M14 12h5M14 18h3"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5V5M12 19v2.5M2.5 12H5M19 12h2.5M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M19.1 4.9l-1.8 1.8M6.7 17.3l-1.8 1.8"/>',
    "tick": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
}


def icon(name: str, cls: str = "") -> Markup:
    attr = f' class="{escape(cls)}"' if cls else ""
    return Markup(f'<svg{attr} viewBox="0 0 24 24">{PATHS[name]}</svg>')
