import math
import brownie
from brownie import Contract
from brownie import config

# test that emergency exit works properly
def test_emergency_exit(
    gov,
    token,
    vault,
    whale,
    strategy,
    chain,
    amount,
    is_slippery,
    no_profit,
    sleep_time,
):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # simulate earnings
    chain.sleep(sleep_time)
    chain.mine(1)
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # set emergency and exit, then confirm that the strategy has no funds
    strategy.setEmergencyExit({"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    assert strategy.estimatedTotalAssets() == 0

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm we made money, or at least that we have about the same
    vault.withdraw({"from": whale})
    if is_slippery and no_profit:
        assert (
            math.isclose(token.balanceOf(whale), startingWhale, abs_tol=10)
            or token.balanceOf(whale) >= startingWhale
        )
    else:
        assert token.balanceOf(whale) >= startingWhale


# test emergency exit, but with a donation (profit)
def test_emergency_exit_with_profit(
    gov,
    token,
    vault,
    whale,
    strategy,
    chain,
    amount,
    is_slippery,
    no_profit,
    sleep_time,
):
    ## deposit to the vault after approving. turn off health check since we're doing weird shit
    strategy.setDoHealthCheck(False, {"from": gov})
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # simulate earnings
    chain.sleep(sleep_time)
    chain.mine(1)
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # set emergency and exit, then confirm that the strategy has no funds
    donation = amount / 2
    token.transfer(strategy, donation, {"from": whale})
    strategy.setDoHealthCheck(False, {"from": gov})
    strategy.setEmergencyExit({"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    assert strategy.estimatedTotalAssets() == 0

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm we made money, or at least that we have about the same
    vault.withdraw({"from": whale})
    if is_slippery and no_profit:
        assert (
            math.isclose(token.balanceOf(whale) + donation, startingWhale, abs_tol=10)
            or token.balanceOf(whale) + donation >= startingWhale
        )
    else:
        assert token.balanceOf(whale) + donation >= startingWhale


# test emergency exit, but after somehow losing all of our assets
def test_emergency_exit_with_loss(
    gov,
    token,
    vault,
    whale,
    strategy,
    chain,
    amount,
    is_slippery,
    no_profit,
    pid,
    is_convex,
    gauge_is_not_tokenized,
):
    ## deposit to the vault after approving. turn off health check since we're doing weird shit
    strategy.setDoHealthCheck(False, {"from": gov})
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

      # our whale donates 1 wei to the vault so we don't divide by zero (0.3.2 vault, errors in vault._reportLoss)
    token.transfer(strategy, 1, {"from": whale})

    # set emergency and exit, then confirm that the strategy has no funds
    strategy.setEmergencyExit({"from": gov})
    strategy.setDoHealthCheck(False, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    assert strategy.estimatedTotalAssets() == 0

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and see how down bad we are
    vault.withdraw({"from": whale})
    print(
        "Raw loss:",
        (startingWhale - token.balanceOf(whale)) / 1e18,
        "Percentage:",
        (startingWhale - token.balanceOf(whale)) / startingWhale,
    )
    print("Share price:", vault.pricePerShare() / 1e18)


# test emergency exit, after somehow losing all of our assets but miraculously getting them recovered
def test_emergency_exit_with_no_loss(
    gov,
    token,
    vault,
    whale,
    strategy,
    chain,
    amount,
    is_slippery,
    no_profit,
    pid,
    is_convex,
    gauge_is_not_tokenized,
):
    ## deposit to the vault after approving. turn off health check since we're doing weird shit
    strategy.setDoHealthCheck(False, {"from": gov})
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    depositSharePrice = vault.pricePerShare()
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # set emergency and exit, then confirm that the strategy has no funds
    strategy.setEmergencyExit({"from": gov})
    strategy.setDoHealthCheck(False, {"from": gov})
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    assert tx.events["Harvested"]["loss"] == 0
    chain.sleep(1)
    assert strategy.estimatedTotalAssets() == 0

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm we have about the same when including convex profit
    whale_profit = (
        (vault.pricePerShare() - depositSharePrice) * vault.balanceOf(whale) / 1e18
    )
    print("Whale profit from other strat PPS increase:", whale_profit / 1e18)
    vault.withdraw({"from": whale})
    profit = token.balanceOf(whale) - startingWhale
    if no_profit and is_slippery:
        assert math.isclose(
            whale_profit, token.balanceOf(whale) - startingWhale, abs_tol=10
        )
    else:
        assert profit > -5  # allow for some slippage here
    print("Whale profit, should be low:", profit / 1e18)


def test_emergency_withdraw_method_0(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    amount,
    sleep_time,
    is_convex,
):
    if not is_convex:
        return

    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # simulate earnings
    chain.sleep(sleep_time)
    chain.mine(1)

    # set emergency exit so no funds will go back to strategy
    # here we assume that the swap out to curve pool tokens is borked, so we stay in cvx vault tokens and send to gov
    # we also assume extra rewards are fine, so we will collect them on harvest and withdrawal
    strategy.setClaimRewards(True, {"from": gov})
    strategy.setEmergencyExit({"from": gov})

    strategy.withdrawToConvexDepositTokens({"from": gov})

    # our whale donates 1 wei to the vault so we don't divide by zero (0.3.2 vault, errors in vault._reportLoss)
    token.transfer(strategy, 1, {"from": whale})

    # turn off health check since we're doing weird shit
    strategy.setDoHealthCheck(False, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    assert strategy.estimatedTotalAssets() == 0
    assert rewardsContract.balanceOf(strategy) == 0
    assert cvxDeposit.balanceOf(strategy) > 0

    # sweep this from the strategy with gov and wait until we can figure out how to unwrap them
    strategy.sweep(cvxDeposit, {"from": gov})
    assert cvxDeposit.balanceOf(gov) > 0


def test_emergency_withdraw_method_1(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    amount,
    sleep_time,
    is_convex,
):
    if not is_convex:
        return

    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})

    # simulate earnings
    chain.sleep(sleep_time)
    chain.mine(1)

    # set emergency exit so no funds will go back to strategy
    # here we assume that the swap out to curve pool tokens is borked, so we stay in cvx vault tokens and send to gov
    # we also assume extra rewards are borked so we don't want them when harvesting or withdrawing
    strategy.setClaimRewards(False, {"from": gov})
    strategy.setEmergencyExit({"from": gov})

    strategy.withdrawToConvexDepositTokens({"from": gov})

    # our whale donates 1 wei to the vault so we don't divide by zero (0.3.2 vault, errors in vault._reportLoss)
    token.transfer(strategy, 1, {"from": whale})

    # turn off health check since we're doing weird shit
    strategy.setDoHealthCheck(False, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.estimatedTotalAssets() == 0
    assert rewardsContract.balanceOf(strategy) == 0
    assert cvxDeposit.balanceOf(strategy) > 0

    strategy.sweep(cvxDeposit, {"from": gov})
    assert cvxDeposit.balanceOf(gov) > 0
