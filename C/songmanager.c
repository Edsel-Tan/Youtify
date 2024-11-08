#include <stdlib.h>
#include "songmanager.h"

void init_sl(SongList *songList) {
    songList->count = 0;
    songList->maxsize = 2;
    songList->songs = malloc(sizeof(Song) * songList->maxsize);
}

void push_back_sl(SongList *songList, Song *song) {
    if (songList->count == songList->maxsize) {
        songList->maxsize *= 2;
        Song *newSongs = malloc(sizeof(Song) * songList->maxsize);
        for (int i = 0; i < songList->count; i++) {
            newSongs[i] = songList->songs[i];
        }
        free(songList->songs);
        songList->songs = newSongs;
    }
    songList->songs[songList->count++] = *song;
}

void delete_sl(SongList *songList) {
    free(songList->songs);
    free(songList);
}