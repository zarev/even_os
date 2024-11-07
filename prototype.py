import asyncio
import flet as ft
from even_glasses.bluetooth_manager import GlassesManager
from even_glasses.commands import send_text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize GlassesManager
manager = GlassesManager()

async def main(page: ft.Page):
    page.title = "Glasses Control Prototype"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20
    page.window_width = 800
    page.window_height = 800

    # Status Text
    status_text = ft.Text(value="Status: Disconnected", size=16)
    
    # Log Output
    log_output = ft.TextField(
        value="",
        read_only=True,
        multiline=True,
        width=600,
        height=200,
    )

    def log_message(message):
        log_output.value += f"{message}\n"
        page.update()

    # Connect Button
    async def connect_glasses(e):
        connect_button.disabled = True
        status_text.value = "Status: Connecting..."
        page.update()
        
        try:
            connected = await manager.scan_and_connect()
            if connected:
                status_text.value = "Status: Connected"
                connect_button.visible = False
                disconnect_button.visible = True
                send_button.disabled = False
                log_message("Successfully connected to glasses!")
            else:
                status_text.value = "Status: Connection Failed"
                log_message("Failed to connect to glasses.")
        except Exception as e:
            status_text.value = "Status: Connection Error"
            log_message(f"Error connecting: {str(e)}")
        finally:
            connect_button.disabled = False
            page.update()

    connect_button = ft.ElevatedButton(
        text="Connect to Glasses",
        on_click=connect_glasses,
        style=ft.ButtonStyle(
            color={
                ft.MaterialState.DEFAULT: ft.colors.WHITE,
                ft.MaterialState.HOVERED: ft.colors.WHITE,
            },
            bgcolor={
                ft.MaterialState.DEFAULT: ft.colors.BLUE,
                ft.MaterialState.HOVERED: ft.colors.BLUE_700,
            },
        ),
    )

    # Disconnect Button
    async def disconnect_glasses(e):
        disconnect_button.disabled = True
        status_text.value = "Status: Disconnecting..."
        page.update()
        
        try:
            await manager.disconnect_all()
            status_text.value = "Status: Disconnected"
            connect_button.visible = True
            disconnect_button.visible = False
            send_button.disabled = True
            log_message("Disconnected from glasses.")
        except Exception as e:
            log_message(f"Error disconnecting: {str(e)}")
        finally:
            disconnect_button.disabled = False
            page.update()

    disconnect_button = ft.ElevatedButton(
        text="Disconnect",
        on_click=disconnect_glasses,
        visible=False,
        style=ft.ButtonStyle(
            color={
                ft.MaterialState.DEFAULT: ft.colors.WHITE,
                ft.MaterialState.HOVERED: ft.colors.WHITE,
            },
            bgcolor={
                ft.MaterialState.DEFAULT: ft.colors.RED,
                ft.MaterialState.HOVERED: ft.colors.RED_700,
            },
        ),
    )

    # Message Input and Send
    message_input = ft.TextField(
        label="Message",
        width=400,
        hint_text="Enter message to display on glasses",
        prefix_icon=ft.icons.MESSAGE,
        border_color=ft.colors.BLUE_400,
    )

    async def send_message(e):
        if not message_input.value:
            return
        
        send_button.disabled = True
        page.update()
        
        try:
            success = await send_text(manager, message_input.value)
            if success:
                log_message(f"Sent message: {message_input.value}")
                message_input.value = ""
            else:
                log_message("Failed to send message")
        except Exception as e:
            log_message(f"Error sending message: {str(e)}")
        finally:
            send_button.disabled = False
            page.update()

    send_button = ft.ElevatedButton(
        text="Send Message",
        on_click=send_message,
        disabled=True,
        style=ft.ButtonStyle(
            color={
                ft.MaterialState.DEFAULT: ft.colors.WHITE,
                ft.MaterialState.HOVERED: ft.colors.WHITE,
            },
            bgcolor={
                ft.MaterialState.DEFAULT: ft.colors.GREEN,
                ft.MaterialState.HOVERED: ft.colors.GREEN_700,
            },
        ),
    )

    # Layout
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            status_text,
                            ft.Row([connect_button, disconnect_button], 
                                  alignment=ft.MainAxisAlignment.CENTER),
                        ], spacing=10),
                        padding=10
                    ),
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("Send Message", size=16, weight=ft.FontWeight.BOLD),
                            message_input,
                            send_button,
                        ], spacing=10),
                        padding=10
                    ),
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("Log", size=16, weight=ft.FontWeight.BOLD),
                            log_output
                        ], spacing=10),
                        padding=10
                    ),
                ),
            ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
        )
    )

    # Monitor connection status
    async def status_monitor():
        while True:
            await asyncio.sleep(1)
            if manager.left_glass and manager.left_glass.client.is_connected:
                status_text.value = "Status: Connected (Left Glass)"
            elif manager.right_glass and manager.right_glass.client.is_connected:
                status_text.value = "Status: Connected (Right Glass)"
            else:
                status_text.value = "Status: Disconnected"
            page.update()

    asyncio.create_task(status_monitor())

if __name__ == "__main__":
    ft.app(target=main, port=8550, view=ft.AppView.WEB_BROWSER)
