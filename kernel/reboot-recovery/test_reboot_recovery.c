/*
 * Testes de unidade da lógica do reboot-recovery (compilados e rodados no host por
 * tests/test_reboot_recovery.py). Sem framework: cada falha imprime a linha e o teste
 * termina com código 1.
 */
#include <stdio.h>
#include <string.h>

#include "reboot_recovery.h"

static int failures;

#define CHECK(cond)                                                       \
	do {                                                              \
		if (!(cond)) {                                            \
			fprintf(stderr, "%s:%d: falhou: %s\n", __FILE__,  \
				__LINE__, #cond);                         \
			failures++;                                       \
		}                                                         \
	} while (0)

static int parse(int argc, char **argv, struct options *opts)
{
	return parse_args(argc, argv, opts);
}

static void test_defaults(void)
{
	char *argv[] = { "reboot-recovery", NULL };
	struct options opts;

	CHECK(parse(1, argv, &opts) == 0);
	CHECK(opts.dry_run == 0);
	CHECK(strcmp(opts.sysrq_path, "/proc/sysrq-trigger") == 0);
	CHECK(strcmp(opts.mounts_path, "/proc/mounts") == 0);
	CHECK(opts.timeout_ms == 10000);
}

static void test_dry_run_and_paths(void)
{
	char *argv[] = { "reboot-recovery", "--dry-run", "--sysrq", "/tmp/s",
			 "--mounts", "/tmp/m", "--timeout-ms", "250", NULL };
	struct options opts;

	CHECK(parse(8, argv, &opts) == 0);
	CHECK(opts.dry_run == 1);
	CHECK(strcmp(opts.sysrq_path, "/tmp/s") == 0);
	CHECK(strcmp(opts.mounts_path, "/tmp/m") == 0);
	CHECK(opts.timeout_ms == 250);
}

static void test_rejects_unknown_and_incomplete(void)
{
	char *unknown[] = { "reboot-recovery", "bootloader", NULL };
	char *missing[] = { "reboot-recovery", "--sysrq", NULL };
	char *bad_number[] = { "reboot-recovery", "--timeout-ms", "x", NULL };
	char *negative[] = { "reboot-recovery", "--timeout-ms", "-5", NULL };
	struct options opts;

	CHECK(parse(2, unknown, &opts) != 0);
	CHECK(parse(2, missing, &opts) != 0);
	CHECK(parse(3, bad_number, &opts) != 0);
	CHECK(parse(3, negative, &opts) != 0);
}

static void test_rw_block_mount_detection(void)
{
	CHECK(is_rw_block_mount("/dev/block/dm-5 /data f2fs rw,lazytime,nosuid 0 0") == 1);
	CHECK(is_rw_block_mount("/dev/block/by-name/cache /cache ext4 rw,seclabel 0 0") == 1);
	CHECK(is_rw_block_mount("/dev/root / ext4 rw,relatime 0 0") == 1);
	CHECK(is_rw_block_mount("/dev/block/dm-0 / ext4 ro,seclabel 0 0") == 0);
	CHECK(is_rw_block_mount("tmpfs /dev tmpfs rw,seclabel 0 0") == 0);
	CHECK(is_rw_block_mount("/dev/fuse /storage/emulated fuse rw,nosuid 0 0") == 0);
	CHECK(is_rw_block_mount("overlay /system overlay ro,seclabel 0 0") == 0);
	CHECK(is_rw_block_mount("/dev/block/dm-7 /x ext4 rwx 0 0") == 0);
	CHECK(is_rw_block_mount("") == 0);
	CHECK(is_rw_block_mount("/dev/block/dm-1") == 0);
}

static void test_count_rw_block_mounts(void)
{
	const char *text =
		"/dev/block/dm-0 / ext4 ro,seclabel 0 0\n"
		"tmpfs /dev tmpfs rw 0 0\n"
		"/dev/block/dm-5 /data f2fs rw,lazytime 0 0\n"
		"/dev/block/by-name/cache /cache ext4 rw 0 0\n"
		"/dev/fuse /storage/emulated fuse rw 0 0\n";
	FILE *f = fmemopen((void *)text, strlen(text), "r");

	CHECK(f != NULL);
	CHECK(count_rw_block_mounts(f) == 2);
	fclose(f);
}

static void test_reboot_request_is_restart2_recovery(void)
{
	struct reboot_request req = build_reboot_request();
	char line[128];

	CHECK(req.magic1 == 0xfee1deadU);
	CHECK(req.magic2 == 0x28121969U);
	CHECK(req.cmd == 0xa1b2c3d4U);
	CHECK(strcmp(req.arg, "recovery") == 0);
	CHECK(format_reboot_request(&req, line, sizeof(line)) > 0);
	CHECK(strcmp(line, "reboot(0xfee1dead, 0x28121969, 0xa1b2c3d4, \"recovery\")") == 0);
}

int main(void)
{
	test_defaults();
	test_dry_run_and_paths();
	test_rejects_unknown_and_incomplete();
	test_rw_block_mount_detection();
	test_count_rw_block_mounts();
	test_reboot_request_is_restart2_recovery();
	if (failures)
		fprintf(stderr, "%d falha(s)\n", failures);
	return failures ? 1 : 0;
}
