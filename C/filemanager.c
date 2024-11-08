#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "songmanager.h"
#include "consts.h"

// Utility functions
void str_replace(char *str, const char *old, const char *new_str) {
    char buffer[1024];
    char *pos = strstr(str, old);
    if (pos == NULL) return;

    int old_len = strlen(old);
    int new_len = strlen(new_str);
    int offset = pos - str;

    strncpy(buffer, str, offset);
    buffer[offset] = '\0';
    strcat(buffer, new_str);
    strcat(buffer, pos + old_len);
    strcpy(str, buffer);
}

void download_song(const char *link, const char *title) {
    char command[1024];
    snprintf(command, sizeof(command), "yt-dlp -x --audio-format wav -o '%s/%s.wav' '%s'", DATA_SONGS, title, link);
    system(command);
}

int load_songs(SongList *songList) {
    FILE *file = fopen(DATA_TXT, "r");
    if (!file) return 2;

    char line[1024];
    while (fgets(line, sizeof(line), file)) {
        str_replace(line, "\n", "");
        str_replace(line, "\'", "");
        char *token = strtok(line, DELIMITER);
        Song *song = malloc(sizeof(Song));

        if (token) {
            strcpy(song->title, token);
        } else {
            return 1;
        }
        token = strtok(NULL, DELIMITER);
        if (token) {
            song->rating = atof(token);
        } else {
            return 1;
        }
        token = strtok(NULL, DELIMITER);
        if (token) {
            song->rating_count = atoi(token);
        } else {
            return 1;
        }
        token = strtok(NULL, DELIMITER);
        if (token) {
            strcpy(song->youtube_link, token);
        } else {
            return 1;
        }
        
        char fname[1024];
        snprintf(fname, sizeof(fname), "%s/%s.%s", DATA_SONGS, song->title, SONG_EXTENSION);
        if (access(fname, F_OK) != 0) {
            printf("%s\n", fname);
            download_song(song->youtube_link, song->title);
        }

        push_back_sl(songList, song);
    }
    fclose(file);
    return 0;
}

void save_songs(SongList *songList) {
    FILE *file = fopen(DATA_TXT, "w");
    for (int i = 0; i < songList->count; i++) {
        Song *song = &songList->songs[i];
        fprintf(file, "%s%s%.2f%s%d%s%s\n", song->title, DELIMITER, song->rating, DELIMITER, song->rating_count, DELIMITER, song->youtube_link);
    }
    fclose(file);
}