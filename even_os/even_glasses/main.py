import asyncio
import json
import flet as ft
import os
from openai import OpenAI, OpenAIError
from even_glasses.bluetooth_manager import GlassesManager
from even_glasses.commands import send_text
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize GlassesManager and OpenAI client
manager = GlassesManager(left_address=None, right_address=None)
openai_client = OpenAI(api_key=os.environ.get("OPENAI_EVEN_OS_KEY"))

# Initialize conversation history
conversation_history = []

async def main(page: ft.Page):
    # Basic page configuration
    page.title = "Glasses Control Panel"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.colors.WHITE
    
    # Configure window size
    page.window = ft.Window(
        width=1000,
        height=800,
        min_width=600,
        min_height=400,
    )
    
    # Web-specific configurations
    page.theme = ft.Theme(
        color_scheme_seed=ft.colors.BLUE,
        font_family="Roboto",
        use_material3=True,
    )
    
    # Make layout responsive
    page.expand = True
    page.scroll = ft.ScrollMode.ADAPTIVE

    connected = False

    # Event Log
    log_output = ft.TextField(
        value="",
        read_only=True,
        multiline=True,
        width=750,
        height=200,
        border_color=ft.colors.GREY_400,
    )

    def log_message(message):
        log_output.value += f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n"
        page.update()

    # Status Components
    def create_status_section():
        status_header = ft.Text(
            value="Glasses Status", size=20, weight=ft.FontWeight.BOLD
        )
        left_status = ft.Text(value="Left Glass: Disconnected", size=14)
        right_status = ft.Text(value="Right Glass: Disconnected", size=14)

        # Add Connect button with web-friendly styling
        connect_button = ft.ElevatedButton(
            text="Connect To Glasses",
            width=200,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.GREEN_400,
            ),
        )

        async def connect_to_glasses(e):
            try:
                log_message("Initiating glasses connection...")
                connect_button.disabled = True
                page.update()

                # Start scanning and connection process
                await manager.start_scanning()
                await asyncio.sleep(2)  # Give some time for scanning
                
                # Try to connect to found devices
                devices = manager.get_discovered_devices()
                if not devices:
                    log_message("No glasses found nearby. Please ensure glasses are powered on and in range.")
                    return

                connection_success = False
                for device in devices:
                    try:
                        if "left" in device.name.lower():
                            await manager.connect_left(device.address)
                            connection_success = True
                        elif "right" in device.name.lower():
                            await manager.connect_right(device.address)
                            connection_success = True
                    except Exception as e:
                        log_message(f"Error connecting to {device.name}: {str(e)}")

                if connection_success:
                    log_message("Successfully connected to glasses!")
                else:
                    log_message("Could not establish connection with glasses.")

            except Exception as e:
                log_message(f"Error during connection: {str(e)}")
            finally:
                connect_button.disabled = False
                await manager.stop_scanning()
                page.update()

        connect_button.on_click = connect_to_glasses

        return (
            ft.Column([
                status_header,
                left_status,
                right_status,
                connect_button
            ], spacing=5),
            left_status,
            right_status,
            connect_button
        )

    # OpenAI Chat Section
    def create_chat_section():
        chat_header = ft.Text(
            value="OpenAI Chat", size=20, weight=ft.FontWeight.BOLD
        )
        chat_input = ft.TextField(
            label="Message to OpenAI",
            width=750,
            multiline=True,
            min_lines=3,
            max_lines=5,
            hint_text="Type your message here...",
            border_color=ft.colors.BLUE_400,
        )
        chat_history = ft.TextField(
            label="Chat History",
            width=750,
            multiline=True,
            read_only=True,
            min_lines=10,
            max_lines=20,
            text_size=14,
            border_color=ft.colors.GREY_400,
        )
        send_button = ft.ElevatedButton(
            text="Send to OpenAI",
            width=200,
            disabled=True,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE_400,
            ),
        )
        clear_button = ft.ElevatedButton(
            text="Clear History",
            width=200,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.RED_400,
            ),
        )
        
        return ft.Column(
            [
                chat_header,
                chat_input,
                chat_history,
                ft.Row(
                    [send_button, clear_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20,
                ),
            ],
            spacing=10,
        ), chat_input, chat_history, send_button, clear_button

    # Create Components
    status_section, left_status, right_status, connect_button = create_status_section()
    chat_section, chat_input, chat_history, send_button, clear_button = create_chat_section()

    async def send_to_openai(e):
        if not chat_input.value:
            return

        user_message = chat_input.value.strip()
        send_button.disabled = True
        page.update()

        try:
            # Add user message to history
            conversation_history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

            # Update chat history display
            chat_history.value = "\n\n".join(
                f"[{msg['timestamp']}] {'You' if msg['role'] == 'user' else 'AI'}: {msg['content']}"
                for msg in conversation_history
            )
            chat_input.value = ""
            page.update()

            # Get OpenAI response
            messages = [{"role": msg["role"], "content": msg["content"]} 
                       for msg in conversation_history]
            
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages
            )
            
            ai_response = response.choices[0].message.content

            # Add AI response to history
            conversation_history.append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

            # Update chat history display
            chat_history.value = "\n\n".join(
                f"[{msg['timestamp']}] {'You' if msg['role'] == 'user' else 'AI'}: {msg['content']}"
                for msg in conversation_history
            )

            # Send to glasses if connected
            if connected:
                await send_text(manager, ai_response)
                log_message("AI response sent to glasses")
            
            log_message("OpenAI chat request completed successfully")
        except OpenAIError as e:
            error_message = f"OpenAI API Error: {str(e)}"
            log_message(error_message)
        except Exception as e:
            error_message = f"Error in OpenAI chat: {str(e)}"
            log_message(error_message)
        finally:
            send_button.disabled = False
            page.update()

    def clear_chat_history(e):
        conversation_history.clear()
        chat_history.value = ""
        log_message("Chat history cleared")
        page.update()

    # Update Status Function
    def on_status_changed():
        nonlocal connected
        left_glass = manager.left_glass
        right_glass = manager.right_glass

        previous_connected = connected

        if left_glass and left_glass.client.is_connected:
            left_status.value = f"Left Glass ({left_glass.name[:13]}): Connected"
        else:
            left_status.value = "Left Glass: Disconnected"

        if right_glass and right_glass.client.is_connected:
            right_status.value = f"Right Glass ({right_glass.name[:13]}): Connected"
        else:
            right_status.value = "Right Glass: Disconnected"

        connected = (
            (left_glass and left_glass.client.is_connected)
            or (right_glass and right_glass.client.is_connected)
        )

        if connected != previous_connected:
            if connected:
                log_message("Glasses connected")
            else:
                log_message("Glasses disconnected")

        send_button.disabled = not connected
        page.update()

    # Assign Event Handlers
    send_button.on_click = send_to_openai
    clear_button.on_click = clear_chat_history

    # Main Layout with web-specific responsive design
    main_content = ft.Column(
        [
            status_section,
            ft.Divider(),
            chat_section,
            ft.Divider(),
            ft.Text(value="Event Log:", size=16, weight=ft.FontWeight.BOLD),
            log_output,
        ],
        spacing=20,
        expand=True,
    )

    page.add(main_content)

    # Background task to monitor status
    async def status_monitor():
        while True:
            await asyncio.sleep(1)
            on_status_changed()

    asyncio.create_task(status_monitor())

if __name__ == "__main__":
    ft.app(
        target=main,
        port=8080,
        host="0.0.0.0",
        view=ft.AppView.WEB_BROWSER,
        web_renderer="html",
        route_url_strategy="path",
        assets_dir="assets",
        web_renderer_config={"canvaskit_enabled": False}  # Disable CanvasKit to avoid GTK dependencies
    )
