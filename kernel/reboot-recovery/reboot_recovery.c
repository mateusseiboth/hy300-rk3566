/*
 * Lógica do reboot-recovery: argumentos, leitura do /proc/mounts e a chamada de reboot.
 * Nada aqui faz I/O no sistema; main.c junta as peças.
 */
#include <stdlib.h>
#include <string.h>

#include "reboot_recovery.h"

/* linux/reboot.h, sem depender dos headers do kernel no host */
#define REBOOT_MAGIC1 0xfee1deadU
#define REBOOT_MAGIC2 0x28121969U
#define REBOOT_CMD_RESTART2 0xa1b2c3d4U
#define REBOOT_TARGET "recovery"

#define DEFAULT_SYSRQ "/proc/sysrq-trigger"
#define DEFAULT_MOUNTS "/proc/mounts"
#define DEFAULT_TIMEOUT_MS 10000

static int parse_timeout(const char *text, long *out)
{
	char *end;
	long value = strtol(text, &end, 10);

	if (*text == '\0' || *end != '\0' || value < 0)
		return -1;
	*out = value;
	return 0;
}

/* Opções com valor: devolve 1 se consumiu o próximo argumento, -1 se é inválida. */
static int parse_valued(const char *name, const char *value, struct options *opts)
{
	if (value == NULL)
		return -1;
	if (strcmp(name, "--sysrq") == 0) {
		opts->sysrq_path = value;
		return 1;
	}
	if (strcmp(name, "--mounts") == 0) {
		opts->mounts_path = value;
		return 1;
	}
	if (strcmp(name, "--timeout-ms") == 0)
		return parse_timeout(value, &opts->timeout_ms) == 0 ? 1 : -1;
	return -1;
}

int parse_args(int argc, char **argv, struct options *opts)
{
	int i;

	opts->dry_run = 0;
	opts->sysrq_path = DEFAULT_SYSRQ;
	opts->mounts_path = DEFAULT_MOUNTS;
	opts->timeout_ms = DEFAULT_TIMEOUT_MS;

	for (i = 1; i < argc; i++) {
		int used;

		if (strcmp(argv[i], "--dry-run") == 0) {
			opts->dry_run = 1;
			continue;
		}
		used = parse_valued(argv[i], i + 1 < argc ? argv[i + 1] : NULL, opts);
		if (used < 0)
			return -1;
		i += used;
	}
	return 0;
}

static int is_block_source(const char *source, size_t len)
{
	static const char block_prefix[] = "/dev/block/";
	static const char root[] = "/dev/root";

	if (len > sizeof(block_prefix) - 1 &&
	    strncmp(source, block_prefix, sizeof(block_prefix) - 1) == 0)
		return 1;
	return len == sizeof(root) - 1 && strncmp(source, root, len) == 0;
}

/*
 * Linha do /proc/mounts: "origem destino tipo opções 0 0". Conta só montagens de
 * dispositivo de bloco: o sysrq 'u' só remonta superblocos com bloco (fuse, tmpfs e
 * overlay continuam rw e não importam).
 */
int is_rw_block_mount(const char *line)
{
	const char *field = line;
	size_t len = strcspn(field, " ");
	int i;

	if (!is_block_source(field, len))
		return 0;
	for (i = 0; i < 3; i++) {
		field += len;
		if (*field != ' ')
			return 0;
		field++;
		len = strcspn(field, " \n");
	}
	return strncmp(field, "rw", 2) == 0 && (field[2] == ',' || field[2] == ' ' || field[2] == '\n' ||
						 field[2] == '\0');
}

int count_rw_block_mounts(FILE *mounts)
{
	char line[1024];
	int count = 0;

	while (fgets(line, sizeof(line), mounts))
		count += is_rw_block_mount(line);
	return count;
}

struct reboot_request build_reboot_request(void)
{
	struct reboot_request req = {
		.magic1 = REBOOT_MAGIC1,
		.magic2 = REBOOT_MAGIC2,
		.cmd = REBOOT_CMD_RESTART2,
		.arg = REBOOT_TARGET,
	};
	return req;
}

int format_reboot_request(const struct reboot_request *req, char *buf, size_t size)
{
	return snprintf(buf, size, "reboot(0x%08x, 0x%08x, 0x%08x, \"%s\")", req->magic1,
			req->magic2, req->cmd, req->arg);
}
