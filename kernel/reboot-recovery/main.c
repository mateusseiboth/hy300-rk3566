/*
 * reboot-recovery: reinicia o HY300 direto para a partição recovery, sem gravar nada na misc.
 *
 * O `adb reboot recovery` do Android 12 grava "boot-recovery" no bootloader_message da
 * misc, e o U-Boot volta para a recovery enquanto o comando estiver lá. Este programa pula
 * o init do Android e pede ao kernel reboot(RESTART2, "recovery"). O driver reboot-mode
 * grava 0x5242c303 no PMU_GRF (0xfdc20200), que sobrevive ao reboot quente e some ao
 * tirar da tomada. O U-Boot lê, sobe a recovery uma vez e volta o registrador para
 * 0x5242c300. Se o kernel de teste travar, tirar da tomada volta ao Android de fábrica.
 *
 * Antes do reboot: sync, sysrq 'u' (remonta só-leitura tudo que tem dispositivo de
 * bloco), espera o /proc/mounts confirmar e sync de novo.
 *
 * Uso (root): reboot-recovery [--dry-run] [--timeout-ms N] [--sysrq ARQ] [--mounts ARQ]
 */
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#include "reboot_recovery.h"

#define POLL_MS 100

static void print_usage(const char *name)
{
	fprintf(stderr, "uso: %s [--dry-run] [--timeout-ms N] [--sysrq ARQ] [--mounts ARQ]\n", name);
}

static int write_sysrq(const char *path, char key)
{
	FILE *f = fopen(path, "w");
	int ok;

	if (f == NULL)
		return -1;
	ok = fputc(key, f) != EOF;
	return (fclose(f) == 0 && ok) ? 0 : -1;
}

static int read_rw_block_mounts(const char *path)
{
	FILE *f = fopen(path, "r");
	int count;

	if (f == NULL)
		return -1;
	count = count_rw_block_mounts(f);
	fclose(f);
	return count;
}

static void sleep_ms(long ms)
{
	struct timespec ts = { .tv_sec = ms / 1000, .tv_nsec = (ms % 1000) * 1000000L };

	while (nanosleep(&ts, &ts) == -1 && errno == EINTR)
		;
}

/* Devolve quantas montagens de bloco ainda estão rw quando o prazo acaba (0 = todas ro). */
static int wait_for_read_only(const char *mounts, long timeout_ms)
{
	long waited = 0;
	int count = read_rw_block_mounts(mounts);

	while (count != 0 && waited < timeout_ms) {
		sleep_ms(POLL_MS);
		waited += POLL_MS;
		count = read_rw_block_mounts(mounts);
	}
	return count;
}

static int run_dry(const struct options *opts, const char *call)
{
	printf("dry-run: sync; 'u' em %s; esperar %s só-leitura (até %ld ms); sync; %s\n",
	       opts->sysrq_path, opts->mounts_path, opts->timeout_ms, call);
	return 0;
}

static void report_remaining(int remaining)
{
	if (remaining > 0)
		printf("aviso: %d montagem(ns) de bloco ainda rw; reiniciando mesmo assim (sync feito)\n",
		       remaining);
	if (remaining < 0)
		printf("aviso: não deu para ler as montagens; reiniciando mesmo assim (sync feito)\n");
}

int main(int argc, char **argv)
{
	struct options opts;
	struct reboot_request req = build_reboot_request();
	char call[128];

	if (parse_args(argc, argv, &opts) != 0) {
		print_usage(argv[0]);
		return 2;
	}
	format_reboot_request(&req, call, sizeof(call));
	if (opts.dry_run)
		return run_dry(&opts, call);

	sync();
	if (write_sysrq(opts.sysrq_path, 'u') != 0) {
		fprintf(stderr, "não deu para escrever em %s (%s); nada foi reiniciado\n",
			opts.sysrq_path, strerror(errno));
		return 1;
	}
	report_remaining(wait_for_read_only(opts.mounts_path, opts.timeout_ms));
	sync();
	printf("%s\n", call);
	fflush(stdout);
	syscall(SYS_reboot, req.magic1, req.magic2, req.cmd, req.arg);
	fprintf(stderr, "reboot falhou: %s\n", strerror(errno));
	return 1;
}
