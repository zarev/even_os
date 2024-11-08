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
    page.title = "Glasses Control Panel"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    page.window_width = 1000
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.colors.WHITE
    page.fonts = {
        "Roboto": "https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap"
    }

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
        return (
            ft.Column([status_header, left_status, right_status], spacing=5),
            left_status,
            right_status,
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
                color={
                    ft.MaterialState.DEFAULT: ft.colors.WHITE,
                    ft.MaterialState.DISABLED: ft.colors.GREY_400,
                },
                bgcolor={
                    ft.MaterialState.DEFAULT: ft.colors.BLUE_400,
                    ft.MaterialState.DISABLED: ft.colors.GREY_200,
                },
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
        
        button_row = ft.Row(
            [send_button, clear_button],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        )
        
        return ft.Column(
            [
                chat_header,
                chat_input,
                chat_history,
                button_row,
            ],
            spacing=10,
        ), chat_input, chat_history, send_button, clear_button

    # Create Components
    status_section, left_status, right_status = create_status_section()
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

    # Main Layout
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
    ft.app(target=main, port=8080, host="0.0.0.0")
