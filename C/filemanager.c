#include <stdio.h>
#include <stdlib.h>
#include "consts.h"

void download_song(const char *link, const char *title) {
    char command[1024];
    snprintf(command, sizeof(command), "yt-dlp -x --audio-format wav -o '%s/%s.wav' '%s'", DATA_SONGS, title, link);
    system(command);
}

void load_songs() {
    FILE *file = fopen(DATA_TXT, "r");
}