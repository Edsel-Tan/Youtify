#include <stdlib.h>
#include "songmanager.h"

void init_sl(SongList *songList) {
    songList->count = 2;
    songList->songs = malloc(sizeof(Song) * songList->count);
}

void push_back_sl(SongList *songList, Song *song) {
    songList->songs[songList->count++] = *song;
}

void delete_sl(SongList *songList) {
    free(songList->songs);
    free(songList);
}