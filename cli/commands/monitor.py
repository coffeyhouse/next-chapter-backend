# cli/commands/monitor.py
import click
import psutil
import time
import platform
from datetime import datetime

def get_cpu_temp():
    """Get CPU temperature across different platforms"""
    if platform.system() == 'Windows':
        try:
            import wmi
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            temperature_infos = w.Sensor()
            for sensor in temperature_infos:
                if sensor.SensorType == 'Temperature' and 'CPU' in sensor.Name:
                    return sensor.Value
        except ImportError:
            click.echo("\nNote: For Windows temperature monitoring:")
            click.echo("1. Download and run OpenHardwareMonitor: https://openhardwaremonitor.org/downloads/")
            click.echo("2. Run: pip install wmi")
            click.echo("3. Keep OpenHardwareMonitor running while monitoring\n")
            return None
        except Exception as e:
            if 'temperature_warning_shown' not in get_cpu_temp.__dict__:
                get_cpu_temp.temperature_warning_shown = True
                click.echo("\nNote: Cannot read CPU temperature. Please ensure OpenHardwareMonitor is running.\n")
            return None
    else:
        # Linux/Mac temperature monitoring
        if hasattr(psutil, 'sensors_temperatures'):
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for sensor_name in ['coretemp', 'cpu_thermal', 'k10temp', 'acpitz']:
                        if sensor_name in temps and temps[sensor_name]:
                            return temps[sensor_name][0].current
            except Exception as e:
                if 'temperature_warning_shown' not in get_cpu_temp.__dict__:
                    get_cpu_temp.temperature_warning_shown = True
                    click.echo(f"\nNote: Cannot read CPU temperature: {str(e)}\n")
                pass
    return None

@click.group()
def monitor():
    """System monitoring commands"""
    pass

@monitor.command()
@click.option('--interval', default=1, help='Interval in seconds between measurements')
@click.option('--count', default=None, type=int, help='Number of measurements to take (default: infinite)')
def cpu(interval: int, count: int):
    """Monitor CPU usage and temperature
    
    Example:
        cli monitor cpu  # Monitor indefinitely with 1s interval
        cli monitor cpu --interval 5  # Monitor every 5 seconds
        cli monitor cpu --count 10  # Take 10 measurements
    """
    measurements = 0
    
    # Print header with system info
    click.echo("\nSystem Information:")
    click.echo(f"CPU: {platform.processor()}")
    click.echo(f"Cores: {psutil.cpu_count()} (Physical: {psutil.cpu_count(logical=False)})")
    click.echo("\nMonitoring CPU (Press Ctrl+C to stop)...\n")
    
    # Track min/max values
    min_usage = 100
    max_usage = 0
    
    try:
        while count is None or measurements < count:
            # Get CPU usage percentage (average over interval)
            cpu_percent = psutil.cpu_percent(interval=1.0)  # More accurate reading
            
            # Update min/max
            min_usage = min(min_usage, cpu_percent)
            max_usage = max(max_usage, cpu_percent)
            
            # Get CPU temperature
            cpu_temp = get_cpu_temp()
                
            # Get current time
            current_time = datetime.now().strftime('%H:%M:%S')
            
            # Determine usage level for color coding
            if cpu_percent < 30:
                color = 'green'
            elif cpu_percent < 70:
                color = 'yellow'
            else:
                color = 'red'
            
            # Print measurements with color
            base_msg = f"[{current_time}] CPU Usage: {click.style(f'{cpu_percent:5.1f}%', fg=color)}"
            if cpu_temp is not None:
                temp_color = 'red' if cpu_temp > 80 else ('yellow' if cpu_temp > 70 else 'green')
                base_msg += f" | Temperature: {click.style(f'{cpu_temp:5.1f}°C', fg=temp_color)}"
            click.echo(base_msg)
            
            measurements += 1
            if count is None or measurements < count:
                time.sleep(max(0, interval - 1))  # Subtract the 1 second used for CPU measurement
                
    except KeyboardInterrupt:
        click.echo("\nMonitoring stopped by user")
    except Exception as e:
        click.echo(f"\nError during monitoring: {str(e)}")
    finally:
        # Print summary
        if measurements > 0:
            click.echo("\nSummary:")
            click.echo(f"Measurements: {measurements}")
            click.echo(f"Min CPU Usage: {min_usage:.1f}%")
            click.echo(f"Max CPU Usage: {max_usage:.1f}%")
            click.echo(f"Average CPU Usage: {(min_usage + max_usage) / 2:.1f}%")

if __name__ == '__main__':
    monitor() 