-- HUMAN RESOURCE MACHINE PROGRAM --
-- 32-Inventory-Report - SIZE 20/16 - SPEED 44/393 --

-- This solution is superseded by 18.32.exploit-LRFLEW.asm, which further
-- optimizes by removing the lookup.

-- Relies on a fixed floor where occurrences are: A=4, B=5, C=2, X=3

    COPYFROM 4
    SUB      1
    COPYTO   2
    COPYTO   3
    BUMPUP   3
    COPYTO   0
    BUMPUP   0
    COPYTO   1
    BUMPUP   1
a:
    INBOX   
    SUB      6
    SUB      1
    JUMPN    b
    COPYFROM 3
    JUMP     c
b:
    ADD      1
    COPYTO   4
    COPYFROM [4]
c:
    OUTBOX  
    JUMP     a


DEFINE LABEL 0
eJzjYWBg6C1ZY/g19V6zULTadiCXobt0hd6fqsm+QV231oH4H9LtcxNz/2TNaduZwTAKRsEoGFYAAEy8
Evo;

DEFINE LABEL 1
eJyTZWBgaItP0TmQaJbOkLSm929SyCqgEINLwntjo3Q947t5W8x5Shkc2MtPurmVX/PnLEsIFyzWilPM
/ZzyKc0sXSXHKOV88Yak7MbC5DltW1Kj2u1zY9t4ypVbZJu1G/X6zWrrZjlXcCy6VNS/TCsrYLlJmvcS
hlEwCkbBoAEAov8sYA;

DEFINE LABEL 2
eJwTZmBgkGvTMthVvcZwdn6pxbLsvbYb0k+6maRd8qlMWRHzK9ksvTJlet3mtB9T12VwLJLJV9s+ofj9
XruqH4eN634cTmjN3SPRobb9YlfEWoZRMApGwZADADRWI9g;

DEFINE LABEL 3
eJzjYWBgEO6yt5drU4xoqDSaJF44f9OHdPfzQGEGxVxvD/6Sg3lfaqumP2yRXLdx2r37DKNgFIyCYQUA
ajQSzQ;

DEFINE LABEL 4
eJxjZ2Bg6C4N8O4o25DEWXarobckYDlQiEG8cLoSwygYBaNg2AMAwLgIxQ;

