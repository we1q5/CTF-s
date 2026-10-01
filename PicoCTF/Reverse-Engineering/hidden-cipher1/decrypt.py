
cipher = bytes.fromhex("3250221656192a48251358110c552f135409")
key = b"S3Cr3t"

plain = bytes(c ^ key[i % len(key)] for i, c in enumerate(cipher))
print(plain.decode())

# the flag is: academy{xor_unpack_4nalys1s_28235a83}