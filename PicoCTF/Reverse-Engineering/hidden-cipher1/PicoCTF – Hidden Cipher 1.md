# Hidden Cipher 1

## Challenge

We are given an encrypted flag:

```text
3250221656192a48251358110c552f135409
```

The challenge also provides a binary and a `flag.txt` file. The local flag is:

```text
academy{fake_flag}
```

The challenge says:

> The flag is right in front of you; just slightly encrypted.

So the goal is to figure out what cipher and key were used.

---

## 1. Running the program

After downloading and extracting the challenge files:

```bash
wget https://challenge-files.cylabacademy.net/library/d2bafb8c63a18489c3b913ce4112d573410495409f1fda6b08edc24ef709fd1e/hiddencipher.zip

unzip hiddencipher.zip
```

The directory contains:

```text
flag.txt
hiddencipher
hiddencipher.zip
```

Running the binary:

```bash
./hiddencipher
```

gives:

```text
Here your encrypted flag:
3250221656192a48251358110c552f135409
```

We already know the corresponding plaintext from `flag.txt`:

```text
academy{fake_flag}
```

This gives us a known plaintext/ciphertext pair to work with.

---

## 2. Looking at the ciphertext as bytes

The encrypted value is hexadecimal, so I converted it into bytes:

```text
32 50 22 16 56 19 2a 48 25 13 58 11 0c 55 2f 13 54 09
```

The known plaintext is:

```text
academy{fake_flag}
```

In hexadecimal:

```text
61 63 61 64 65 6d 79 7b 66 61 6b 65 5f 66 6c 61 67 7d
```

---

## 3. Finding the key

The important clue is that XOR encryption can be reversed with XOR again:

```text
ciphertext XOR plaintext = key
```

So I XORed the two byte sequences.

The result was:

```text
53 33 43 72 33 74 53 33 43 72 33 74 53 33 43 72 33 74
```

Converting those bytes to ASCII gives:

```text
S3Cr3tS3Cr3tS3Cr3t
```

So the actual repeating key is:

```text
S3Cr3t
```

That means the program is using a repeating-key XOR cipher.

---

## 4. Testing the key locally

I verified the key with a small Python script:

```python
cipher = bytes.fromhex("3250221656192a48251358110c552f135409")
key = b"S3Cr3t"

plain = bytes(c ^ key[i % len(key)] for i, c in enumerate(cipher))
print(plain.decode())
```

The output was:

```text
academy{fake_flag}
```

So the key and cipher are correct.

---

## 5. Connecting to the remote service

The challenge provides the following server:

```bash
nc chatelaine.cylabacademy.net 12625
```

Running it gives a different ciphertext:

```text
3250221656192a483b1d412b265d3313501f0c072d135f0d2002302d014c610076130b472e
```

Since we already discovered that the cipher is repeating-key XOR with:

```text
S3Cr3t
```

we can decrypt the remote ciphertext with the same Python script.

```python
cipher = bytes.fromhex(
    "3250221656192a483b1d412b265d3313501f0c072d135f0d2002302d014c610076130b472e"
)

key = b"S3Cr3t"

plain = bytes(c ^ key[i % len(key)] for i, c in enumerate(cipher))
print(plain.decode())
```

The result is:

```text
academy{xor_unpack_4nalys1s_28235a83}
```

---

## Flag

```text
academy{xor_unpack_4nalys1s_28235a83}
```

---

## What I learned

The main technique in this challenge was recognizing a known-plaintext XOR situation.

Because we had both:

```text
academy{fake_flag}
```

and its encrypted version, we could calculate:

```text
plaintext XOR ciphertext = key
```

which revealed the repeating key:

```text
S3Cr3t
```

After that, the remote ciphertext could be decrypted using the same repeating-key XOR operation.