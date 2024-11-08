import asyncio
import json
import flet as ft
import os
from openai import OpenAI, OpenAIError
from even_glasses.bluetooth_manager import GlassesManager
from even_glasses.commands import send_text, send_rsvp, send_notification
from even_glasses.models import NCSNotification, RSVPConfig
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize GlassesManager and OpenAI client
manager = GlassesManager(left_address=None, right_address=None)
openai_client = OpenAI(api_key=os.environ.get("OPENAI_EVEN_OS_KEY"))

# Initialize conversation threads
conversation_threads = {
    "General": []  # Default thread
}
current_thread = "General"

async def main(page: ft.Page):
    page.title = "Glasses Control Panel"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    connected = False

    # Event Log
    log_output = ft.TextField(
        value="",
        read_only=True,
        multiline=True,
        width=750,
        height=200,
    )

    def log_message(message):
        log_output.value += message + "\n"
        page.update()

    # Status Components
    def create_status_section():
        status_header = ft.Text(
            value="Glasses Status", size=20, weight=ft.FontWeight.BOLD
        )
        left_status = ft.Text(value="Left Glass: Disconnected", size=14)
        right_status = ft.Text(value="Right Glass: Disconnected", size=14)
        return ft.Column([status_header, left_status, right_status], spacing=5), left_status, right_status

    # OpenAI Chat Section with Threading
    def create_openai_chat_section():
        chat_header = ft.Text(
            value="OpenAI Chat", size=18, weight=ft.FontWeight.BOLD
        )
        
        # Thread selection dropdown
        thread_dropdown = ft.Dropdown(
            width=300,
            label="Select Thread",
            value=current_thread,
            options=[ft.dropdown.Option(thread) for thread in conversation_threads.keys()]
        )
        
        # New thread creation
        new_thread_input = ft.TextField(
            label="New Thread Name",
            width=200
        )
        create_thread_button = ft.ElevatedButton(
            text="Create Thread",
            disabled=False
        )
        
        chat_input = ft.TextField(
            label="Enter your message",
            width=750,
            multiline=True,
            min_lines=2,
            max_lines=5
        )
        
        chat_history = ft.TextField(
            label="Conversation History",
            width=750,
            multiline=True,
            read_only=True,
            min_lines=5,
            max_lines=15,
            text_size=14
        )
        
        send_chat_button = ft.ElevatedButton(
            text="Send to OpenAI",
            disabled=False
        )
        
        clear_history_button = ft.ElevatedButton(
            text="Clear History",
            disabled=False
        )

        thread_controls = ft.Row(
            [thread_dropdown, new_thread_input, create_thread_button],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20
        )

        return (
            ft.Column(
                [
                    chat_header,
                    thread_controls,
                    chat_input,
                    chat_history,
                    ft.Row(
                        [send_chat_button, clear_history_button],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=20,
                    ),
                ],
                spacing=10,
            ),
            chat_input,
            chat_history,
            send_chat_button,
            clear_history_button,
            thread_dropdown,
            new_thread_input,
            create_thread_button
        )

    # Create all sections
    status_section, left_status, right_status = create_status_section()
    (
        chat_section,
        chat_input,
        chat_history,
        send_chat_button,
        clear_history_button,
        thread_dropdown,
        new_thread_input,
        create_thread_button
    ) = create_openai_chat_section()

    def update_chat_history():
        """Update the chat history display for the current thread"""
        formatted_history = ""
        for msg in conversation_threads[current_thread]:
            timestamp = msg.get("timestamp", "")
            role = "You" if msg["role"] == "user" else "AI"
            formatted_history += f"[{timestamp}] {role}: {msg['content']}\n\n"
        chat_history.value = formatted_history
        page.update()

    def update_thread_dropdown():
        """Update the thread dropdown options"""
        thread_dropdown.options = [ft.dropdown.Option(thread) for thread in conversation_threads.keys()]
        page.update()

    async def send_chat_message(e):
        if not chat_input.value:
            return

        user_message = chat_input.value.strip()
        send_chat_button.disabled = True
        chat_input.value = ""
        page.update()

        try:
            # Add user message to history with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conversation_threads[current_thread].append({
                "role": "user",
                "content": user_message,
                "timestamp": timestamp
            })
            update_chat_history()

            # Create messages array with conversation history for the current thread
            messages = [{"role": m["role"], "content": m["content"]} 
                       for m in conversation_threads[current_thread]]
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            
            ai_response = response.choices[0].message.content
            
            # Add AI response to history with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conversation_threads[current_thread].append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": timestamp
            })
            update_chat_history()
            
            # Send to glasses if connected
            if connected:
                await send_text(manager, ai_response)
                log_message(f"Sent AI response to glasses")
            
            log_message(f"OpenAI chat request completed successfully")
        except OpenAIError as e:
            error_message = f"OpenAI API Error: {str(e)}"
            log_message(error_message)
        except Exception as e:
            error_message = f"Error processing chat request: {str(e)}"
            log_message(error_message)
        finally:
            send_chat_button.disabled = False
            page.update()

    def clear_chat_history(e):
        """Clear the conversation history for the current thread"""
        conversation_threads[current_thread].clear()
        update_chat_history()
        log_message(f"Chat history cleared for thread: {current_thread}")

    def switch_thread(e):
        """Switch to selected thread"""
        global current_thread
        current_thread = thread_dropdown.value
        update_chat_history()
        log_message(f"Switched to thread: {current_thread}")

    def create_new_thread(e):
        """Create a new conversation thread"""
        thread_name = new_thread_input.value.strip()
        if thread_name and thread_name not in conversation_threads:
            conversation_threads[thread_name] = []
            new_thread_input.value = ""
            update_thread_dropdown()
            thread_dropdown.value = thread_name
            switch_thread(None)
            log_message(f"Created new thread: {thread_name}")
        else:
            log_message("Invalid thread name or thread already exists")

    # Assign Event Handlers
    send_chat_button.on_click = send_chat_message
    clear_history_button.on_click = clear_chat_history
    thread_dropdown.on_change = switch_thread
    create_thread_button.on_click = create_new_thread

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
            await asyncio.sleep(1)  # Check every 1 second
            on_status_changed()

    asyncio.create_task(status_monitor())

ft.app(target=main)
