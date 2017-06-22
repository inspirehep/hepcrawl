// This is needed to be able to run with suid enabled, as most modern linuxes
// don't honoor it on scripts (shell, python, ...) due to security reasons.
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

// This path is hardcoded because we don't need it to be flexible, and that
// simplifies this program security-wise.
char *VENV_PATH = "/hepcrawl_venv/";
char *CODE_PATH = "/code/";
char *TMP_PATH = "/tmp/";


int main (int argc, char *argv[]) {
    char *chown_argv[] = {
        "/usr/bin/chown",
        "--recursive",
        NULL,
        // This will be replaced by the <uid:gid> passed as argument.
        NULL,
        NULL
        // This last NULL is required to 'flag' the end of the options.
    };
    char *chown_env[] = { NULL };
    int status;
    int cureuid;

    if (argc != 3) {
        fprintf(
            stderr,
            "Usage: %s --virtualenv|--codedir|--tmpdir <user>:<group>\n",
            argv[0]
        );
        exit(EXIT_FAILURE);
    }

    // set the user:group parameter
    chown_argv[2] = argv[2];

    if (strcmp(argv[1], "--virtualenv") == 0) {
        // virtualenv permissions
        chown_argv[3] = VENV_PATH;
    } else if (strcmp(argv[1], "--codedir") == 0) {
        // code dir permissions
        chown_argv[3] = CODE_PATH;
    } else if (strcmp(argv[1], "--tmpdir") == 0) {
        // tmp dir permissions
        chown_argv[3] = TMP_PATH;
    } else {
        fprintf(stderr, "Bad option %s.", argv[1]);
        fprintf(
            stderr,
            "Usage: %s --virtualenv|--codedir|--tmpdir <user>:<group>\n",
            argv[0]
        );
        exit(EXIT_FAILURE);
    }
    execve(chown_argv[0], chown_argv, chown_env);
}
