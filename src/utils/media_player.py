

class SongItem:
    def __init__(self, name, album, artist):
        self.name = name
        self.album = album
        self.artist = artist

class MediaPlayer:
    def __init__(self):
        print("MEDIA PLAYER NOT IMPLEMENTED")

    def play_song(self, song: SongItem):
        print(song)

    def queue_song(self, path):
        return None
    
    def queue_album(self, path):
        return None
    
    def queue_artist(self, path):
        return None
    
media_player = MediaPlayer()