# adversarial-iac judge

Score a match by comparing Red Team manifest to Blue Team findings.

## Usage

```bash
adversarial-iac judge --red-dir <path> --blue-dir <path> [OPTIONS]
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--red-dir`, `-r` | path | required | Directory with Red Team output (manifest) |
| `--blue-dir`, `-b` | path | required | Directory with Blue Team findings |
| `--output-dir`, `-o` | path | output/scoring | Output directory |

## Examples

### Score a match

```bash
adversarial-iac judge -r output/red-team -b output/red-team
```

(Blue Team writes findings into the same directory when run with `-i output/red-team`.)

### Custom output

```bash
adversarial-iac judge -r output/red-team -b output/red-team -o output/scores
```

## Output

Writes scoring results (precision, recall, F1, evasion rate) to the output directory.
