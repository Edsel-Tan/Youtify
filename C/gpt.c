#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <pthread.h>
#include <errno.h>
#include <time.h>
#include <signal.h>

#define DATA_FOLDER "data"
#define DATA_TXT DATA_FOLDER "/data.txt"
#define DATA_SONGS DATA_FOLDER "/songs"
#define DELIMITER "%%%"
#define SONG_EXTENSION ".wav"
#define VOLUME_ADJUSTMENT -20

// Data structures
typedef struct {
    char title[256];
    char youtube_link[512];
    float rating;
    int rating_count;
} Song;

typedef struct {
    Song *songs;
    int count;
} SongList;

// Global Variables
SongList song_list;
int volume_adjustment = VOLUME_ADJUSTMENT;

// Function prototypes
void menu();
void load_songs();
void save_songs();
void add_song();
// void display_songs();
void download_song(const char *link, const char *title);
void play_song(const char *title);
// void edit_song();
void create_playlist();
void recommend_song();
void set_volume();
void redownload_songs();
void verify_songs();
void play_audio(const char *filename);
size_t write_data(void *ptr, size_t size, size_t nmemb, FILE *stream);

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

void create_directories() {
    struct stat st = {0};

    if (stat(DATA_FOLDER, &st) == -1) {
        mkdir(DATA_FOLDER, 0700);
    }
    if (stat(DATA_SONGS, &st) == -1) {
        mkdir(DATA_SONGS, 0700);
    }
}

void menu() {
    int option;
    do {
        printf("\n1) R-Recommend\n");
        printf("2) P-Playlist\n");
        printf("3) D-Display\n");
        printf("4) A-Add\n");
        printf("5) E-Edit\n");
        printf("6) V-Volume\n");
        printf("7) RDL-Redownload\n");
        printf("8) B-Break\n");

        printf("\nEnter your choice: ");
        char command[2];
        scanf("%s", command);
        switch (command[0]) {
            case 'r':
                recommend_song();
                break;
            case 'p':
                create_playlist();
                break;
            case 'a':
                add_song();
                break;
            case 'v':
                set_volume();
                break;
            case 'd':
                redownload_songs();
                break;
            case 'b':
                exit(0);
                break;
            default:
                printf("Invalid option, try again.\n");
        }
    } while (1);
}

void load_songs() {
    FILE *file = fopen(DATA_TXT, "r");
    if (!file) return;

    song_list.count = 0;
    song_list.songs = malloc(sizeof(Song) * 100); // Pre-allocate space for 100 songs

    char line[1024];
    while (fgets(line, sizeof(line), file)) {
        str_replace(line, "\n", "");
        char *token = strtok(line, DELIMITER);
        if (token) strcpy(song_list.songs[song_list.count].title, token);
        token = strtok(NULL, DELIMITER);
        if (token) song_list.songs[song_list.count].rating = atof(token);
        token = strtok(NULL, DELIMITER);
        if (token) song_list.songs[song_list.count].rating_count = atoi(token);
        token = strtok(NULL, DELIMITER);
        if (token) strcpy(song_list.songs[song_list.count].youtube_link, token);
        song_list.count++;
    }
    fclose(file);
}

void save_songs() {
    FILE *file = fopen(DATA_TXT, "w");
    for (int i = 0; i < song_list.count; i++) {
        Song *song = &song_list.songs[i];
        fprintf(file, "%s%s%.2f%s%d%s%s\n", song->title, DELIMITER, song->rating, DELIMITER, song->rating_count, DELIMITER, song->youtube_link);
    }
    fclose(file);
}

void download_song(const char *link, const char *title) {
    char command[1024];
    snprintf(command, sizeof(command), "yt-dlp -x --audio-format wav -o '%s/%s.wav' '%s'", DATA_SONGS, title, link);
    system(command);
}

void play_audio(const char *filename) {
    char command[256];
    snprintf(command, sizeof(command), "ffplay -nodisp -autoexit '%s'", filename);
    system(command);
}

void recommend_song() {
    if (song_list.count == 0) {
        printf("No songs available.\n");
        return;
    }
    int random_index = rand() % song_list.count;
    play_song(song_list.songs[random_index].title);
}

void add_song() {
    char title[256];
    char link[512];
    printf("Enter song title: ");
    scanf("%s", title);
    printf("Enter YouTube link: ");
    scanf("%s", link);

    Song new_song;
    strcpy(new_song.title, title);
    strcpy(new_song.youtube_link, link);
    new_song.rating = 0;
    new_song.rating_count = 0;

    download_song(link, title);

    song_list.songs[song_list.count++] = new_song;
    save_songs();
}

void create_playlist() {
    int playlist_size;
    printf("Enter preferred playlist size: ");
    scanf("%d", &playlist_size);
    if (playlist_size > song_list.count) playlist_size = song_list.count;

    for (int i = 0; i < playlist_size; i++) {
        int random_index = rand() % song_list.count;
        play_song(song_list.songs[random_index].title);
    }
}

void play_song(const char *title) {
    char filepath[512];
    snprintf(filepath, sizeof(filepath), "%s/%s.wav", DATA_SONGS, title);
    play_audio(filepath);
}

void set_volume() {
    printf("Enter volume adjustment (current: %d): ", volume_adjustment);
    scanf("%d", &volume_adjustment);
}

void redownload_songs() {
    for (int i = 0; i < song_list.count; i++) {
        download_song(song_list.songs[i].youtube_link, song_list.songs[i].title);
    }
}

void verify_songs() {
    for (int i = 0; i < song_list.count; i++) {
        char filepath[512];
        snprintf(filepath, sizeof(filepath), "%s/%s.wav", DATA_SONGS, song_list.songs[i].title);
        if (access(filepath, F_OK) == -1) {
            // File does not exist, redownload
            download_song(song_list.songs[i].youtube_link, song_list.songs[i].title);
        }
    }
}

int main() {
    srand(time(NULL));
    create_directories();
    load_songs();
    verify_songs();
    menu();
    return 0;
}
