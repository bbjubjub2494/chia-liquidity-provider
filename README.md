# Hybrid liquidity farming with Chia offers
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
![License](https://img.shields.io/github/license/bbjubjub2494/chia-liquidity-provider)


Implementation of a grid trading strategy for [Chia offers]
with support for XCH-CAT and CAT-CAT pairs.


## How it works

The system takes inspiration from the concept of *range orders* from [Uniswap v3].
Simply put,
a range order is an offer to buy some quantity of an asset
that then turns into a sell order at a slightly higher price when fullfilled.
Each time the market price goes back and forth around the order,
the operator gets to keep the difference as profit.

Unlike Uniswap, this system requires an off-chain component to watch the offers,
and publish new offers each time to a decentralized exchange such as [Dexie].

That's all there is to it!
Okay, the only thing left to do is to allocate the initial liquidity.
For that, the [Uniswap v3] concentrated liquidity formula is a good starting point.
Since Dexie users appear to prefer to swap in round numbers,
one strategy is to set the XCH amount to e.g. `0.1`
and vary the other side of the offer to fit the curve.


## Usage

`clp init` should be used to create the initial offers.
It expects the given wallet to contain appropriately split coins.

`clp show-init` will indicate the expected coins.

`clp manage` can be run as a daemon to watch trades
with the help of the Chia light wallet.
Only offers created through the `init` command and recorded in the `clp` database
will be taken into account.
If trades are performed while `clp manage` is not running,
it will flip them as soon as it catches up.


## TODO

- manipulate offers directly to avoid weird race conditions
- robustness against reorgs
- support multiple positions independently


## Wen moon?

I made `0.1 XCH` in two weeks, it's for fun more so than profit.
I consider it an achievement.

[Chia offers]: https://www.chia.net/offers/
[Uniswap v3]: https://uniswap.org/whitepaper-v3.pdf
[Dexie]: https://dexie.space/
