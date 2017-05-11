// This is needed to be able to run with suid enabled, as most modern linuxes
// don't honoor it on scripts (shell, python, ...) due to security reasons.
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/wait.h>

// This path is hardcoded because we don't need it to be flexible, and that
// simplifies this program security-wise.
char *VENV_PATH = "/hepcrawl_venv/";
char *TMP_PATH = "/tmp/";


int main (int argc, char *argv[]) {
    char *chown_argv[] = {
        "/usr/bin/chown",
        "--recursive",
        NULL,
        // This will be replaced by the <uid:gid> passed as argument.
        VENV_PATH,
        TMP_PATH,
        NULL
        // This last NULL is required to 'flag' the end of the options.
    };
    char *chown_env[] = { NULL };
    int status;
    int cureuid;

    if (argc != 2) {
        fprintf(stderr, "Usage: %s <user>:<gorup>\n", argv[0]);
        exit(EXIT_FAILURE);
    }

    chown_argv[2] = argv[1];
    execve(chown_argv[0], chown_argv, chown_env);
}
