all: largefile.bin hash

largefile.bin:
	dd if=/dev/zero of=$@ bs=1M count=1024

hash: largefile.bin
	sha1sum -b largefile.bin moby-dick.pdf > hashes.txt

check:
	sha1sum -c hashes.txt

.PHONY: clean
clean:
	rm -f largefile.bin hashes.txt
