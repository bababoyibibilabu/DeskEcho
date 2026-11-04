import sys
from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray, QSize, Qt

# Google Material Symbols (Rounded / Outlined) inlined clean SVGs
MATERIAL_SYMBOLS = {
    "light_mode": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58a.996.996 0 00-1.41 0 .996.996 0 000 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37a.996.996 0 00-1.41 0 .996.996 0 000 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41l-1.06-1.06zm1.06-10.96a.996.996 0 000-1.41.996.996 0 00-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05 18.36a.996.996 0 000-1.41.996.996 0 00-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z"/></svg>""",
    "dark_mode": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/></svg>""",
    "search": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>""",
    "mic": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>""",
    "bolt": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M11 21h-1l1-7H7.5c-.88 0-.33-.75-.31-.78C8.48 10.94 10.42 7.54 13 3h1l-1 7h3.5c.49 0 .56.33.47.51l-.07.15C12.96 17.55 11 21 11 21z"/></svg>""",
    "chat": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/></svg>""",
    "history": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M13 3a9 9 0 0 0-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0 0 13 21a9 9 0 0 0 0-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/></svg>""",
    "rocket_launch": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M9.19 6.35c-2.04 2.29-3.44 5.58-3.57 5.89-.19.46-.07.99.3 1.33l2.51 2.51c.27.27.65.41 1.02.37.38-.04.72-.25.92-.58.18-.3 1.48-2.31 3.55-4.4 2.87-2.89 6.27-4.49 6.41-4.56.45-.22.73-.67.73-1.17v-1.74c0-.55-.45-1-1-1h-1.74c-.5 0-.95.28-1.17.73-.07.14-1.67 3.54-4.56 6.41l-.4.39zM12 2.5c4.74 0 8.78 3.32 9.77 7.79l-2.05.41C18.96 7.42 15.75 4.5 12 4.5c-4.14 0-7.5 3.36-7.5 7.5 0 2.24.99 4.26 2.56 5.63l-1.39 1.44C3.81 17.38 2.5 14.84 2.5 12c0-5.25 4.25-9.5 9.5-9.5z"/></svg>""",
    "settings": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>""",
    "apartment": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M17 11V3H7v4H3v14h8v-4h2v4h8V11h-4zM7 19H5v-2h2v2zm0-4H5v-2h2v2zm0-4H5V9h2v2zm4 4H9v-2h2v2zm0-4H9V9h2v2zm0-4H9V5h2v2zm4 8h-2v-2h2v2zm0-4h-2V9h2v2zm0-4h-2V5h2v2zm4 12h-2v-2h2v2zm0-4h-2v-2h2v2z"/></svg>""",
    "keyboard": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M20 5H4c-1.1 0-1.99.9-1.99 2L2 17c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm-9 3h2v2h-2V8zm0 3h2v2h-2v-2zM8 8h2v2H8V8zm0 3h2v2H8v-2zm-1 2H5v-2h2v2zm0-3H5V8h2v2zm9 7H8v-2h8v2zm0-4h-2v-2h2v2zm0-3h-2V8h2v2zm3 3h-2v-2h2v2zm0-3h-2V8h2v2z"/></svg>""",
    "volume_up": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>""",
    "volume_off": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/></svg>""",
    "article": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>""",
    "delete": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M16 9v10H8V9h8m-1.5-6h-5l-1 1H5v2h14V4h-3.5l-1-1zM18 7H6v12c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7z"/></svg>""",
    "segment": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M9 18h12v-2H9v2zM3 6v2h18V6H3zm6 7h12v-2H9v2z"/></svg>""",
    "auto_delete": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M16 9v10H8V9h8m-1.5-6h-5l-1 1H5v2h14V4h-3.5l-1-1zM18 7H6v12c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7z"/></svg>""",
    "group": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>""",
    "tune": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z"/></svg>""",
    "content_copy": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>""",
    "stop_circle": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-3-12h6c.55 0 1 .45 1 1v6c0 .55-.45 1-1 1H9c-.55 0-1-.45-1-1V9c0-.55.45-1 1-1z"/></svg>""",
    "delete_forever": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zm2.46-7.12l1.41-1.41L12 12.59l2.12-2.12 1.41 1.41L13.41 14l2.12 2.12-1.41 1.41L12 15.41l-2.12 2.12-1.41-1.41L10.59 14l-2.13-2.12zM15.5 4l-1-1h-5l-1 1H5v2h14V4z"/></svg>""",
    "warning": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>""",
    "info": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>""",
    "check_circle": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>""",
    "add": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>""",
    "arrow_forward": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/></svg>""",
    "arrow_back": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>""",
    "chevron_left": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>""",
    "chevron_right": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg>""",
    "visibility": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>""",
    "visibility_off": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.44-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"/></svg>""",
    "save": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z"/></svg>""",
    "play_arrow": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M8 5v14l11-7z"/></svg>""",
    "delete_sweep": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M15 16h4v2h-4zm0-8h7v2h-7zm0 4h6v2h-6zM3 18c0 1.1.9 2 2 2h6c1.1 0 2-.9 2-2V8H3v10zm2-8h6v8H5v-8zm5-6H6L5 5H2v2h12V5h-3z"/></svg>""",
    "auto_awesome": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M19 9l1.25-2.75L23 5l-2.75-1.25L19 1l-1.25 2.75L15 5l2.75 1.25L19 9zm-7.5.5L9 4 6.5 9.5 1 12l5.5 2.5L9 20l2.5-5.5L17 12l-5.5-2.5zM19 15l-1.25 2.75L15 19l2.75 1.25L19 23l1.25-2.75L23 19l-2.75-1.25L19 15z"/></svg>""",
    "graphic_eq": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M7 18h2V6H7v12zm4 4h2V2h-2v20zm-8-8h2v-4H3v4zm12 4h2V6h-2v12zm4-8v4h2v-4h-2z"/></svg>""",
    "extension": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M20.5 11H19V7c0-1.1-.9-2-2-2h-4V3.5a2.5 2.5 0 0 0-5 0V5H4c-1.1 0-1.99.9-1.99 2v3.8H3.5c1.49 0 2.7 1.21 2.7 2.7s-1.21 2.7-2.7 2.7H2V20c0 1.1.9 2 2 2h3.8v-1.5c0-1.49 1.21-2.7 2.7-2.7s2.7 1.21 2.7 2.7V22H17c1.1 0 2-.9 2-2v-4h1.5a2.5 2.5 0 0 0 0-5z"/></svg>""",
    "psychology": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}"><path d="M13 2.05v2.02c3.95.49 7 3.85 7 7.93 0 2.48-1.13 4.7-2.89 6.16l1.37 1.48C20.67 17.84 22 15.08 22 12c0-5.18-3.95-9.45-9-9.95zM4.03 12c0-4.08 3.06-7.44 7.01-7.93V2.05C5.99 2.55 2.03 6.82 2.03 12c0 2.55.96 4.87 2.54 6.64l1.45-1.39C4.78 15.82 4.03 14 4.03 12zm9 4.95v2.02c1.98-.32 3.73-1.34 4.97-2.77l-1.42-1.42c-.93 1.13-2.22 1.9-3.55 2.17zm-4.04.01c-1.33-.28-2.61-1.04-3.54-2.17L4.03 16.2c1.24 1.44 2.99 2.46 4.97 2.78v-2.02z"/></svg>""",
}

def get_symbol_pixmap(name: str, color: str = "#26B0E4", size: int = 18) -> QPixmap:
    template = MATERIAL_SYMBOLS.get(name)
    if not template:
        # Fallback empty
        pix = QPixmap(size, size)
        pix.fill(QColor(0, 0, 0, 0))
        return pix
        
    svg_str = template.format(color=color)
    renderer = QSvgRenderer(QByteArray(svg_str.encode('utf-8')))
    
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    return pix

def get_symbol_icon(name: str, color: str = "#26B0E4", size: int = 18) -> QIcon:
    return QIcon(get_symbol_pixmap(name, color=color, size=size))

def get_flower_logo_pixmap(size: int = 32) -> QPixmap:
    """加载美好智能花朵 Logo (支持 PyInstaller 打包与源码直跑)"""
    candidates = [
        Path(sys.executable).parent / "assets" / "flower_logo.png",
        Path(__file__).parent.parent.parent / "assets" / "flower_logo.png",
        Path("assets/flower_logo.png"),
    ]
    if hasattr(sys, "_MEIPASS"):
        candidates.insert(0, Path(sys._MEIPASS) / "assets" / "flower_logo.png")

    for p in candidates:
        if p.exists():
            pix = QPixmap(str(p))
            if not pix.isNull():
                return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    # 兜底纯色渐变
    pix = QPixmap(size, size)
    pix.fill(QColor("#26B0E4"))
    return pix

def get_flower_logo_icon(size: int = 32) -> QIcon:
    return QIcon(get_flower_logo_pixmap(size))
