from dotenv import load_dotenv
import os
import pygame
import time

# Load environment
load_dotenv()
LIBRARY = os.getenv("LIBRARY")

if not LIBRARY:
    raise ValueError("No LIBRARY env variable defined")

# Import app components
from src.cache.cache_manager import CacheManager
from src.player.music_player import MusicPlayer
from src.player.queue_manager import QueueManager
from src.ui.renderer import Renderer
from src.ui.ui_manager import UIManager
from src.utils.constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, HOLD_TIME_MS

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("PIPOD Music Player")
clock = pygame.time.Clock()

# Initialize cache
cache_manager = CacheManager(LIBRARY)
songs, albums, artists = cache_manager.load_or_build()
print(f"DEBUG: Loaded {len(songs)} songs, {len(albums)} albums, {len(artists)} artists")

# Initialize players
music_player = MusicPlayer()
print(f"DEBUG: Music player initialized, VLC available: {music_player.is_vlc_available()}")

queue_manager = QueueManager()
print("DEBUG: Queue manager initialized")

# Initialize UI
renderer = Renderer(screen)
print("DEBUG: Renderer initialized")

ui_manager = UIManager(renderer, songs, albums, artists)
print("DEBUG: UI manager initialized")

# State
running = True
now_playing = False
right_arrow_held = False
right_arrow_held_time = 0


def handle_player_action(action):
    """Handle music player actions."""
    global now_playing

    if action == "prev":
        song = queue_manager.prev()
        if song:
            music_player.previous()
            pos, total = queue_manager.get_queue_position()
            ui_manager.update_now_playing(song, pos, total, music_player.is_playing, queue_manager.shuffle_enabled)

    elif action == "next":
        song = queue_manager.next()
        if song:
            music_player.next()
            pos, total = queue_manager.get_queue_position()
            ui_manager.update_now_playing(song, pos, total, music_player.is_playing, queue_manager.shuffle_enabled)
        else:
            # Queue finished
            if ui_manager.current_view != ui_manager.now_playing:
                now_playing = False

    elif action == "toggle_pause":
        music_player.toggle_pause()
        song = queue_manager.get_current_song()
        if song:
            pos, total = queue_manager.get_queue_position()
            ui_manager.update_now_playing(song, pos, total, music_player.is_playing, queue_manager.shuffle_enabled)


def queue_and_play_song():
    """Queue and play selected song."""
    global now_playing
    # Get all songs for queuing
    selected_song = ui_manager.get_selected_song_for_play()
    if not selected_song:
        return

    # Determine what to queue
    if ui_manager.current_view == ui_manager.songs_view:
        # Queue all songs from current view
        queue_manager.queue_all_songs(ui_manager.songs_view.items_data)
    else:
        # Just this song
        queue_manager.add_song(selected_song)

    # Load playlist to music player
    queue_files = [s.path for s in queue_manager.queue]
    music_player.load_playlist(queue_files)
    music_player.play()
    now_playing = True

    # Switch to now playing view
    song = queue_manager.get_current_song()
    if song:
        pos, total = queue_manager.get_queue_position()
        ui_manager.switch_to_now_playing(song, pos, total, music_player.is_playing, queue_manager.shuffle_enabled)

# Main loop
last_render_time = 0
render_throttle = 1.0 / FPS  # Throttle renders to FPS
frame_count = 0

while running:
    frame_count += 1
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print("DEBUG: QUIT event received")
            running = False
        elif event.type == pygame.KEYDOWN:
            # Track right arrow hold for now playing button
            if event.key == pygame.K_RIGHT:
                right_arrow_held = True
                right_arrow_held_time = time.time()

            # Handle navigation and actions
            if event.key == pygame.K_LEFT:
                print("DEBUG: LEFT pressed")
                ui_manager.handle_input(event.key)
            elif event.key in (pygame.K_UP, pygame.K_DOWN):
                print(f"DEBUG: {['UP', 'DOWN'][event.key == pygame.K_DOWN]} pressed, selection before: {ui_manager.current_view.selected_index}")
                ui_manager.handle_input(event.key)
                print(f"DEBUG: selection after: {ui_manager.current_view.selected_index}")
            elif event.key == pygame.K_RIGHT:
                if now_playing:
                    # In now playing view, RIGHT = pause/play
                    handle_player_action("toggle_pause")
                # else: will handle on KEYUP based on hold duration

        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_RIGHT:
                right_arrow_held = False
                held_duration = (time.time() - right_arrow_held_time) * 1000
                print(f"DEBUG: RIGHT released, held_duration: {held_duration}ms, now_playing: {now_playing}")

                if held_duration < HOLD_TIME_MS and not now_playing:
                    print("DEBUG: Short press in non-playing mode - calling handle_input")
                    # Short press: select/enter on current view
                    result = ui_manager.handle_input(pygame.K_RIGHT)
                    print(f"DEBUG: handle_input returned: {result}, current_view: {ui_manager.current_view.__class__.__name__}")
                    # If in songs view, play the selected song
                    if ui_manager.current_view == ui_manager.songs_view:
                        selected = ui_manager.get_selected_song_for_play()
                        if selected:
                            queue_and_play_song()
                elif held_duration >= HOLD_TIME_MS and now_playing:
                    print("DEBUG: Long press in playing mode - jumping to now playing")
                    # Long press: jump to now playing if audio is playing
                    song = queue_manager.get_current_song()
                    if song:
                        pos, total = queue_manager.get_queue_position()
                        ui_manager.switch_to_now_playing(song, pos, total, music_player.is_playing, queue_manager.shuffle_enabled)
                else:
                    print(f"DEBUG: No action - held_duration<HOLD_TIME_MS={held_duration < HOLD_TIME_MS}, not now_playing={not now_playing}")

    # Render UI
    ui_manager.render()

    # Draw now playing button if audio is playing and not in now playing view
    if now_playing and ui_manager.current_view != ui_manager.now_playing:
        song = queue_manager.get_current_song()
        if song:
            ui_manager.draw_now_playing_button(song)

    pygame.display.flip()

# Cleanup
pygame.quit()
# music_player.stop()
