/* Lógica testável do reboot-recovery (sem efeito colateral). */
#ifndef HY300_REBOOT_RECOVERY_H
#define HY300_REBOOT_RECOVERY_H

#include <stdio.h>

struct options {
	int dry_run;
	const char *sysrq_path;
	const char *mounts_path;
	long timeout_ms;
};

struct reboot_request {
	unsigned int magic1;
	unsigned int magic2;
	unsigned int cmd;
	const char *arg;
};

int parse_args(int argc, char **argv, struct options *opts);
int is_rw_block_mount(const char *line);
int count_rw_block_mounts(FILE *mounts);
struct reboot_request build_reboot_request(void);
int format_reboot_request(const struct reboot_request *req, char *buf, size_t size);

#endif
