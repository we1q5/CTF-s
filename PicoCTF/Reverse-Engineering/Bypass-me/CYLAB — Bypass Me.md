# Bypass Me

## Challenge

**Challenge:** Bypass Me  
**Platform:** CYLAB Academy  
**Category:** Reverse Engineering / Binary Analysis

The challenge provides a password-protected Linux binary called `bypassme.bin`.

The goal is to reverse engineer the program, figure out how authentication works, and access the flag.

---

## 1. Getting the Binary

I connected to the challenge server over SSH and downloaded the binary to my local machine so I could analyze it with LLDB.

```bash
scp -P 36519 ctf-player@xebec.cylabacademy.net:/home/ctf-player/bypassme.bin .
```

I first checked what kind of file I was dealing with:

```bash
file bypassme.bin
```

It was an x86-64 PIE ELF executable with debug information.

I also ran:

```bash
checksec --file=bypassme.bin
```

The binary had modern protections enabled, including:

- Full RELRO
- Stack Canary
- NX
- PIE

So this was not going to be a simple memory-corruption challenge. I decided to focus on understanding the program's logic.

---

## 2. Looking at the Strings

I started with:

```bash
strings -n 5 bypassme.bin
```

Some interesting strings immediately stood out:

```text
Authenticating
Access to this terminal is restricted.
Please authenticate below.
[ %d tries left] Enter password:
Raw Input: [%s]
Sanitized Input:[%s]
Hint: Input must match something special...
../../root/flag.txt
Flag: %s
Access Denied
```

There were also several useful function names:

```text
sanitize
decode_password
auth_sequence
intro_sequence
```

The presence of `decode_password()` looked particularly interesting.

---

## 3. Finding the Important Functions

I loaded the binary into LLDB:

```bash
lldb ./bypassme.bin
```

Then I checked where the interesting functions were:

```lldb
image lookup -rn 'sanitize|decode_password|auth_sequence|main'
```

The binary contained debug information, so LLDB was able to identify the functions and even the original source file and line numbers.

The important functions were:

```text
decode_password()
sanitize()
auth_sequence()
main()
```

I decided to start with `decode_password()`.

---

## 4. Reversing decode_password()

I disassembled the function:

```lldb
disassemble -n decode_password
```

One of the most interesting instructions was:

```asm
movabsq $-0x3630062730252007, %rax
...
movl $0xcfd8dfc9, -0xc(%rbp)
```

The function then loops over the bytes and performs:

```asm
xorl $-0x56, %eax
```

The low byte of `-0x56` is:

```text
0xAA
```

So the function is XORing every byte with `0xAA`.

The loop continues for 11 bytes and then adds a null terminator.

In simplified pseudocode, the function is doing something like:

```c
for (int i = 0; i <= 10; i++) {
    out[i] = encoded[i] ^ 0xAA;
}

out[11] = '\0';
```

At this point I could have decoded the bytes manually, but LLDB gave me an easier way to verify the result.

I set a breakpoint on the function:

```lldb
breakpoint set --name decode_password
```

After stepping through the function, LLDB displayed:

```text
decode_password(out="SuperSecure")
```

So the decoded password was:

```text
SuperSecure
```

---

## 5. Investigating the Sanitizer

The challenge description made the input sanitizer sound important, so I wanted to understand exactly what it did.

I disassembled it:

```lldb
disassemble -n sanitize
```

The function calls `isalpha()` on every input character.

The important logic is:

```asm
callq  0x11a0
testl  %eax, %eax
je     ...
```

If `isalpha()` returns true, the character is copied into the sanitized buffer.

This means the sanitizer effectively behaves like:

```c
for (int i = 0; input[i] != '\0'; i++) {
    if (isalpha(input[i])) {
        sanitized[j++] = input[i];
    }
}

sanitized[j] = '\0';
```

So non-alphabetic characters are removed.

For example:

```text
Input:      S3c@ure123
Sanitized:  Secure
```

That looked interesting, but I still needed to see whether the sanitized value was actually used for authentication.

---

## 6. Checking main()

I disassembled `main()`:

```lldb
disassemble -n main
```

The program first calls:

```asm
callq 0x13c2
```

which is `sanitize()`.

The two buffers are:

```text
-0x210(%rbp) → user input
-0x190(%rbp) → sanitized input
```

The program then prints both values:

```text
Raw Input: [...]
Sanitized Input:[...]
```

The important part comes later:

```asm
lea    -0x110(%rbp), %rdx
lea    -0x210(%rbp), %rax
movq   %rdx, %rsi
movq   %rax, %rdi
callq  0x1180
testl  %eax, %eax
jne    ...
```

On x86-64 Linux, the first function argument is passed in `RDI` and the second in `RSI`.

Therefore:

```text
RDI → raw input
RSI → decoded password
```

The call at `0x1180` is the `strcmp()` call.

So the program is effectively doing:

```c
strcmp(input, decoded_password);
```

rather than:

```c
strcmp(sanitized, decoded_password);
```

This means the sanitized string is displayed, but it is not what is used for the password comparison.

---

## 7. Testing the Password

At this point I had recovered the password:

```text
SuperSecure
```

I ran the binary and entered it:

```text
[3 tries left] Enter password: SuperSecure

Raw Input:      [SuperSecure]
Sanitized Input:[SuperSecure]

Authenticating...
```

The program accepted the password and continued to the flag-reading stage.

On my local copy I received:

```text
Flag file not found.
```

This made sense because the local machine did not contain the challenge's:

```text
../../root/flag.txt
```

The important part was that authentication had succeeded.

I then ran the binary on the challenge environment using the recovered password, where the flag file was actually present.

---

## 8. Conclusion

The main things I discovered were:

1. `decode_password()` stores an encoded password in the binary.
2. Each byte is XORed with `0xAA`.
3. The resulting password is:

```text
SuperSecure
```

4. `sanitize()` removes non-alphabetic characters.
5. However, `main()` passes the **raw input** to `strcmp()` instead of the sanitized buffer.
6. Entering the recovered password successfully bypasses the authentication barrier and reaches the flag-reading code.

This challenge was a good exercise in following program flow instead of assuming that every security-related function is actually part of the security check.