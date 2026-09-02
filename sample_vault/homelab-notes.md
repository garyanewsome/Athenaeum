# Homelab Notes

## GPU passthrough

Considered GPU passthrough for a VM at one point, decided against it —
bare-metal Ollama is simpler and the RTX 3060 only needs to serve one
consumer for now.

## Storage layout

Went with LVM pooled across both drives, but pinned the storage volume
to a single physical disk to keep failure isolation. Root stays small
on purpose — most of the space is intentionally left unallocated for
future logical volumes.
