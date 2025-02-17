import click
from typing import List, Any, Callable, Optional

def create_progress_bar(
    items: List[Any],
    label: str = 'Processing',
    item_name_func: Optional[Callable[[Any], str]] = None,
    show_item_progress: bool = True
) -> click.progressbar:
    """Create a standardized progress bar that shows overall progress and, optionally, the current item."""
    return click.progressbar(
        items,
        label=click.style(label, fg='blue'),
        item_show_func=lambda x: click.style(item_name_func(x), fg='cyan') if (item_name_func and show_item_progress) else None,
        show_eta=True,
        show_percent=True,
        width=50
    )

def nested_progress_bar(total: int, label: str = 'Subtasks') -> click.progressbar:
    """Create a progress bar for tracking subtasks within an item."""
    return click.progressbar(
        range(total),
        label=click.style(label, fg='magenta'),
        show_eta=True,
        show_percent=True,
        width=30
    )
