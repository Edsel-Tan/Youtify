#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include "consts.h"
#include "filemanager.h"
#include "songmanager.h"

void play_audio(const char *filename) {
    char command[1024];
    snprintf(command, sizeof(command), "ffplay -nodisp -autoexit '%s'", filename);
    system(command);
}

void play_song(const char *title) {
    char filepath[1024];
    snprintf(filepath, sizeof(filepath), "%s/%s.wav", DATA_SONGS, title);
    play_audio(filepath);
}

void recommend_song(SongList *songList) {
    if (songList->count == 0) {
        printf("No songs available.\n");
        return;
    }
    int random_index = rand() % songList->count;
    play_song(songList->songs[random_index].title);
}

int main() {
    SongList songList;
    
    init_sl(&songList);
    int status = load_songs(&songList);
    if (status) {
        return status;
    }

    recommend_song(&songList);
}