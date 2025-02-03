import click
from pathlib import Path
import os

@click.group()
def dev():
    """Development helper commands"""
    pass

@dev.command()
@click.option('--output', default="directory_structure.txt", help='Output file path')
def structure(output: str):
    """Output directory structure to file"""
    click.echo(f"\nGenerating directory structure to: {output}")
    
    EXCLUDE_DIRS = {
        '.git', '__pycache__', 'backend',
        'author_photos', 'book_covers', 'exported_html'
    }
    DATA_FOLDER_ONLY = {'data'}
    
    def should_skip_dir(path: Path) -> bool:
        return path.name in EXCLUDE_DIRS
        
    def get_structure(path: Path, indent: str = "", is_root: bool = False) -> list[str]:
        lines = []
        
        if not is_root:
            # Add folder (skip for root level)
            lines.append(f"{indent}+-- {path.name}/")
        
        # Check if we're in a data folder (only show directories, no files)
        in_data_folder = any(parent.name in DATA_FOLDER_ONLY for parent in path.parents)
        
        # Process contents
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        next_indent = "" if is_root else indent + "|   "
        
        for item in items:
            if item.is_dir():
                if should_skip_dir(item):
                    continue
                    
                lines.extend(get_structure(item, next_indent))
            elif not in_data_folder and not is_root:  # Only include files if not in data folder and not root
                # Check if file is empty
                is_empty = item.stat().st_size == 0
                empty_marker = " [empty]" if is_empty else ""
                lines.append(f"{indent}|-- {item.name}{empty_marker}")
                
        return lines
    
    try:
        # Get structure starting from current directory, marking it as root
        structure = get_structure(Path.cwd(), is_root=True)
        
        # Write to file with UTF-8 encoding
        with open(output, 'w', encoding='utf-8') as f:
            f.write("\n".join(structure))
            
        click.echo(click.style("\nStructure written successfully", fg='green'))
        
    except Exception as e:
        click.echo(click.style(f"\nError generating structure: {e}", fg='red'))

@dev.command()
@click.option('--output-dir', default="combined_files", help='Output directory for combined files')
def combine(output_dir: str):
    """Combine non-empty files within each subfolder into single txt files"""
    click.echo(f"\nCombining files into directory: {output_dir}")
    
    EXCLUDE_DIRS = {
        '.git', '__pycache__', 'backend',
        'author_photos', 'book_covers', 'exported_html',
        'data', 'combined_files'  # Don't process data dir or our output dir
    }
    
    EXCLUDE_EXTENSIONS = {'.pyc', '.db', '.jpg', '.png', '.gif'}
    
    def should_skip_dir(path: Path) -> bool:
        return path.name in EXCLUDE_DIRS or path.name.startswith('.')
    
    def should_include_file(path: Path) -> bool:
        # Skip empty files and files with excluded extensions
        return (path.stat().st_size > 0 and 
                path.suffix.lower() not in EXCLUDE_EXTENSIONS and
                not path.name.startswith('.'))
    
    def process_directory(dir_path: Path, output_base: Path, is_root: bool = False):
        # Skip excluded directories
        if should_skip_dir(dir_path):
            return
            
        # Collect all non-empty files in this directory
        files_content = []
        for item in dir_path.iterdir():
            if item.is_file() and should_include_file(item):
                try:
                    content = item.read_text(encoding='utf-8')
                    # Get relative path from the root directory
                    rel_path = str(item.relative_to(Path.cwd())).replace('/', '\\')
                    
                    # Check if content already starts with a separator
                    header = f"# {rel_path}\n\n"
                    if not content.startswith("# "):
                        files_content.append(f"{header}{content}\n\n")
                    else:
                        files_content.append(f"{content}\n\n")
                except Exception as e:
                    click.echo(click.style(f"Error reading {item}: {e}", fg='yellow'))
        
        # If we found any files, combine them
        if files_content and not is_root:
            # Create simplified filename from directory path
            rel_dir = str(dir_path.relative_to(Path.cwd()))
            simplified_name = rel_dir.replace('\\', '-').replace('/', '-') + '.txt'
            
            output_file = output_base / simplified_name
            try:
                output_file.write_text("\n".join(files_content), encoding='utf-8')
                click.echo(f"Created combined file: {output_file}")
            except Exception as e:
                click.echo(click.style(f"Error writing {output_file}: {e}", fg='red'))
        
        # Process subdirectories
        for item in dir_path.iterdir():
            if item.is_dir():
                process_directory(item, output_base, False)
    
    try:
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Start processing from current directory
        process_directory(Path.cwd(), output_path, is_root=True)
        
        click.echo(click.style("\nFiles combined successfully", fg='green'))
        
    except Exception as e:
        click.echo(click.style(f"\nError combining files: {e}", fg='red'))