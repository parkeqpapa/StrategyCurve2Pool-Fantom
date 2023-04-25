import pytest
from brownie import config, Wei, Contract, chain, ZERO_ADDRESS
import requests

# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# set this for if we want to use tenderly or not; mostly helpful because with brownie.reverts fails in tenderly forks.
use_tenderly = False


################################################## TENDERLY DEBUGGING ##################################################

# change autouse to True if we want to use this fork to help debug tests
@pytest.fixture(scope="session", autouse=use_tenderly)
def tenderly_fork(web3, chain):
    fork_base_url = "https://simulate.yearn.network/fork"
    payload = {"network_id": str(chain.id)}
    resp = requests.post(fork_base_url, headers={}, json=payload)
    fork_id = resp.json()["simulation_fork"]["id"]
    fork_rpc_url = f"https://rpc.tenderly.co/fork/{fork_id}"
    print(fork_rpc_url)
    tenderly_provider = web3.HTTPProvider(fork_rpc_url, {"timeout": 600})
    web3.provider = tenderly_provider
    print(f"https://dashboard.tenderly.co/yearn/yearn-web/fork/{fork_id}")


################################################ UPDATE THINGS BELOW HERE ################################################


@pytest.fixture(scope="session")
def tests_using_tenderly():
    yes_or_no = use_tenderly
    yield yes_or_no


# use this to set what chain we use. 1 for ETH, 250 for fantom
chain_used = 250

# put our pool's convex pid here
@pytest.fixture(scope="session")
def pid():
    pid = 40  # mim 40, FRAX 32
    yield pid


# this is the amount of funds we have our whale deposit. adjust this as needed based on their wallet balance
@pytest.fixture(scope="session")
def amount():
    amount = 35_000e18  # use 35k for MIM, 140k for FRAX
    yield amount




@pytest.fixture(scope="session")
def whale(accounts, amount, token):
    # Totally in it for the tech
    # Update this with a large holder of your want token (the largest EOA holder of LP)
    # MIM 0xe896e539e557BC751860a7763C8dD589aF1698Ce, FRAX 0x839Bb033738510AA6B4f78Af20f066bdC824B189
    whale = accounts.at("0x8866414733F22295b7563f9C5299715D2D76CAf4", force=True)
    if token.balanceOf(whale) < 2 * amount:
        raise ValueError(
            "Our whale needs more funds. Find another whale or reduce your amount variable."
        )
    yield whale


# use this if your vault is already deployed
@pytest.fixture(scope="session")
def vault_address():
    vault_address = "0x2DfB14E32e2F8156ec15a2c21c3A6c053af52Be8"
    # MIM 0x2DfB14E32e2F8156ec15a2c21c3A6c053af52Be8
    # FRAX 0xB4AdA607B9d6b2c9Ee07A275e9616B84AC560139
    yield vault_address


# curve deposit pool for old pools, set to ZERO_ADDRESS otherwise
@pytest.fixture(scope="session")
def old_pool():
    old_pool = ZERO_ADDRESS
    yield old_pool


# this is the name we want to give our strategy
@pytest.fixture(scope="session")
def strategy_name():
    strategy_name = "StrategyCurve2CRV"
    yield strategy_name


# this is the name of our strategy in the .sol file
@pytest.fixture(scope="session")
def contract_name(StrategyCurve2Pool):
    contract_name = StrategyCurve2Pool 
    yield contract_name


# this is the address of our rewards token
@pytest.fixture(scope="session")
def rewards_token():  # OGN 0x8207c1FfC5B6804F6024322CcF34F29c3541Ae26, SPELL 0x090185f2135308BaD17527004364eBcC2D37e5F6
    # SNX 0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F
    yield Contract("0x27e611fd27b276acbd5ffd632e5eaebec9761e40")


# sUSD gauge uses blocks instead of seconds to determine rewards, so this needs to be true for that to test if we're earning
@pytest.fixture(scope="session")
def try_blocks():
    try_blocks = False  # True for sUSD
    yield try_blocks


# whether or not we should try a test donation of our rewards token to make sure the strategy handles them correctly
# if you want to bother with whale and amount below, this needs to be true
@pytest.fixture(scope="session")
def test_donation():
    test_donation = True
    yield test_donation


@pytest.fixture(scope="session")
def rewards_whale(accounts):
    # SNX whale: 0x8D6F396D210d385033b348bCae9e4f9Ea4e045bD, >600k SNX
    # SPELL whale: 0x46f80018211D5cBBc988e853A8683501FCA4ee9b, >10b SPELL
    yield accounts.at("0x46f80018211D5cBBc988e853A8683501FCA4ee9b", force=True)


@pytest.fixture(scope="session")
def rewards_amount():
    rewards_amount = 1_000_000e18
    # SNX 50_000e18
    # SPELL 1_000_000e18
    yield rewards_amount


# whether or not a strategy is clonable. if true, don't forget to update what our cloning function is called in test_cloning.py
@pytest.fixture(scope="session")
def is_clonable():
    is_clonable = False 
    yield is_clonable


# whether or not a strategy has ever had rewards, even if they are zero currently. essentially checking if the infra is there for rewards.
@pytest.fixture(scope="session")
def rewards_template():
    rewards_template = True  # MIM True, FRAX False
    yield rewards_template


# this is whether our pool currently has extra reward emissions (SNX, SPELL, etc)
@pytest.fixture(scope="session")
def has_rewards():
    has_rewards = False  # False for both
    yield has_rewards


# this is whether our strategy is convex or not
@pytest.fixture(scope="session")
def is_convex():
    is_convex = False
    yield is_convex


# if our curve gauge deposits aren't tokenized (older pools), we can't as easily do some tests and we skip them
@pytest.fixture(scope="session")
def gauge_is_not_tokenized():
    gauge_is_not_tokenized = False
    yield gauge_is_not_tokenized


# use this to test our strategy in case there are no profits
@pytest.fixture(scope="session")
def no_profit():
    no_profit = False
    yield no_profit


# use this when we might lose a few wei on conversions between want and another deposit token
# generally this will always be true if no_profit is true, even for curve/convex since we can lose a wei converting
@pytest.fixture(scope="session")
def is_slippery(no_profit):
    is_slippery = False
    if no_profit:
        is_slippery = True
    yield is_slippery


# use this to set the standard amount of time we sleep between harvests.
# generally 1 day, but can be less if dealing with smaller windows (oracles) or longer if we need to trigger weekly earnings.
@pytest.fixture(scope="session")
def sleep_time():
    hour = 3600

    # change this one right here
    hours_to_sleep = 6  # 6 for MIM and FRAX

    sleep_time = hour * hours_to_sleep
    yield sleep_time


################################################ UPDATE THINGS ABOVE HERE ################################################

# Only worry about changing things above this line, unless you want to make changes to the vault or strategy.
# ----------------------------------------------------------------------- #

if chain_used == 1:  # mainnet

    @pytest.fixture(scope="session")
    def sushi_router():  # use this to check our allowances
        yield Contract("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")

    # all contracts below should be able to stay static based on the pid
    @pytest.fixture(scope="session")
    def booster():  # this is the deposit contract
        yield Contract("0xF403C135812408BFbE8713b5A23a04b3D48AAE31")

    @pytest.fixture(scope="session")
    def voter():
        yield Contract("0xF147b8125d2ef93FB6965Db97D6746952a133934")

    @pytest.fixture(scope="session")
    def convexToken():
        yield Contract("0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B")

    @pytest.fixture(scope="session")
    def crv():
        yield Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")

    @pytest.fixture(scope="session")
    def other_vault_strategy():
        yield Contract("0x8423590CD0343c4E18d35aA780DF50a5751bebae")

    @pytest.fixture(scope="session")
    def proxy():
        yield Contract("0xA420A63BbEFfbda3B147d0585F1852C358e2C152")

    @pytest.fixture(scope="session")
    def curve_registry():
        yield Contract("0x90E00ACe148ca3b23Ac1bC8C240C2a7Dd9c2d7f5")

    @pytest.fixture(scope="session")
    def curve_cryptoswap_registry():
        yield Contract("0x4AacF35761d06Aa7142B9326612A42A2b9170E33")

    @pytest.fixture(scope="session")
    def healthCheck():
        yield Contract("0xDDCea799fF1699e98EDF118e0629A974Df7DF012")

    @pytest.fixture(scope="session")
    def farmed():
        # this is the token that we are farming and selling for more of our want.
        yield Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")

   # @pytest.fixture(scope="session")
   # def token(pid, booster):
        # this should be the address of the ERC-20 used by the strategy/vault
    #    token_address = booster.poolInfo(pid)[0]
     #   yield Contract(token_address)

    @pytest.fixture(scope="session")
    def cvxDeposit(booster, pid):
        # this should be the address of the convex deposit token
        cvx_address = booster.poolInfo(pid)[1]
        yield Contract(cvx_address)

    @pytest.fixture(scope="session")
    def rewardsContract(pid, booster):
        rewardsContract = booster.poolInfo(pid)[3]
        yield Contract(rewardsContract)

    # gauge for the curve pool
    @pytest.fixture(scope="session")
    def gauge(pid, booster):
        gauge = booster.poolInfo(pid)[2]
        yield Contract(gauge)

    # curve deposit pool
    @pytest.fixture(scope="session")
    def pool(token, curve_registry, curve_cryptoswap_registry, old_pool):
        if old_pool == ZERO_ADDRESS:
            if curve_registry.get_pool_from_lp_token(token) == ZERO_ADDRESS:
                if (
                    curve_cryptoswap_registry.get_pool_from_lp_token(token)
                    == ZERO_ADDRESS
                ):
                    poolContract = token
                else:
                    poolAddress = curve_cryptoswap_registry.get_pool_from_lp_token(
                        token
                    )
                    poolContract = Contract(poolAddress)
            else:
                poolAddress = curve_registry.get_pool_from_lp_token(token)
                poolContract = Contract(poolAddress)
        else:
            poolContract = Contract(old_pool)
        yield poolContract

    @pytest.fixture(scope="session")
    def gasOracle():
        yield Contract("0xb5e1CAcB567d98faaDB60a1fD4820720141f064F")

    # Define any accounts in this section
    # for live testing, governance is the strategist MS; we will update this before we endorse
    # normal gov is ychad, 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52
    @pytest.fixture(scope="session")
    def gov(accounts):
        yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)

    @pytest.fixture(scope="session")
    def strategist_ms(accounts):
        # like governance, but better
        yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    # set all of these accounts to SMS as well, just for testing
    @pytest.fixture(scope="session")
    def keeper(accounts):
        yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    @pytest.fixture(scope="session")
    def rewards(accounts):
        yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    @pytest.fixture(scope="session")
    def guardian(accounts):
        yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    @pytest.fixture(scope="session")
    def management(accounts):
        yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    @pytest.fixture(scope="session")
    def strategist(accounts):
        yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    @pytest.fixture(scope="module")
    def vault(pm, gov, rewards, guardian, management, token, chain, vault_address):
        if vault_address == ZERO_ADDRESS:
            Vault = pm(config["dependencies"][0]).Vault
            vault = guardian.deploy(Vault)
            vault.initialize(token, gov, rewards, "", "", guardian)
            vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
            vault.setManagement(management, {"from": gov})
            chain.sleep(1)
            chain.mine(1)
        else:
            vault = Contract(vault_address)
        yield vault

    # replace the first value with the name of your strategy
  
elif chain_used == 250:  # only fantom so far and convex doesn't exist there

   
    @pytest.fixture(scope="session")
    def crv():
        yield Contract("0x1E4F97b9f9F913c46F1632781732927B9019C68b")

    
        
        # curve deposit pool
            # Define any accounts in this section
    # for live testing, governance is the strategist MS; we will update this before we endorse
    # normal gov is ychad, 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52
    @pytest.fixture(scope="session")
    def gov(accounts):
        yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)

    @pytest.fixture(scope="session")
    def strategist_ms(accounts):
        # like governance, but better
        yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    @pytest.fixture(scope="session")
    def keeper(accounts):
        yield accounts.at("0xBedf3Cf16ba1FcE6c3B751903Cf77E51d51E05b8", force=True)

    @pytest.fixture(scope="session")
    def rewards(accounts):
        yield accounts.at("0x8Ef63b525fceF7f8662D98F77f5C9A86ae7dFE09", force=True)

    @pytest.fixture(scope="session")
    def guardian(accounts):
        yield accounts[2]

    @pytest.fixture(scope="session")
    def management(accounts):
        yield accounts[3]

    @pytest.fixture(scope="session")
    def other_vault_strategy():
        yield Contract("0xfF8bb7261E4D51678cB403092Ae219bbEC52aa51")

    @pytest.fixture(scope="session")
    def strategist(accounts):
        yield accounts[4]

    @pytest.fixture(scope="session")
    def token():
        token_address = "0x27E611FD27b276ACbd5Ffd632E5eAEBEC9761E40"  # this should be the address of the ERC-20 used by the strategy/vault (DAI)
        yield Contract(token_address)

    @pytest.fixture(scope="session")
    def farmed():
        yield Contract("0x1E4F97b9f9F913c46F1632781732927B9019C68b") # CRV

    @pytest.fixture(scope="session")
    def healthCheck():
        yield Contract("0xf13Cd6887C62B5beC145e30c38c4938c5E627fe0")

    @pytest.fixture(scope="session")
    def gasOracle():
        yield Contract("0xb5e1CAcB567d98faaDB60a1fD4820720141f064F")

    @pytest.fixture(scope="session")
    def no_profit():
        no_profit = False
        yield no_profit

    @pytest.fixture(scope="session")
    def is_slippery(no_profit):
        is_slippery = False
        if no_profit:
            is_slippery = True
        yield is_slippery


    @pytest.fixture(scope="module")
    def vault(pm, gov, rewards, guardian, management, token, chain):
            Vault = pm(config["dependencies"][0]).Vault
            vault = guardian.deploy(Vault)
            vault.initialize(token, gov, rewards, "", "", guardian)
            vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
            vault.setManagement(management, {"from": gov})
            chain.sleep(1)
            chain.mine(1)
            yield vault
   
    @pytest.fixture(scope="module")
    def strategy(
        contract_name,
        strategist,
        keeper,
        vault,
        gov,
        guardian,
        token,
        chain,
        pid,
        strategy_name,
        strategist_ms,
        is_convex,
        rewards_token,
        has_rewards,
        vault_address,
        try_blocks,
    ):
        if is_convex:
            # make sure to include all constructor parameters needed here
            strategy = strategist.deploy(
                contract_name,
                vault,
                pid,
                pool,
                strategy_name,
            )
            print("\nConvex strategy")
        else:
            # make sure to include all constructor parameters needed here
            strategy = strategist.deploy(
                contract_name,
                vault,

            )
            print("\nCurve strategy")

        strategy.setKeeper(keeper, {"from": gov})

        # set our management fee to zero so it doesn't mess with our profit checking
        vault.setManagementFee(0, {"from": gov})

          # if we have other strategies, set them to zero DR and remove them from the queue
        if vault_address != ZERO_ADDRESS:
            for i in range(0, 20):
                strat_address = vault.withdrawalQueue(i)
                if ZERO_ADDRESS == strat_address:
                    break

                    if vault.strategies(strat_address)["debtRatio"] > 0:
                        vault.updateStrategyDebtRatio(strat_address, 0, {"from": gov})
                        interface.ICurveStrategy045(strat_address).harvest({"from": gov})
                        vault.removeStrategyFromQueue(strat_address, {"from": gov})

        vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

    # turn our oracle into testing mode by setting the provider to 0x00, then forcing true
        

    # this is the same for new or existing vaults
        yield strategy




# commented-out fixtures to be used with live testing

# # list any existing strategies here
# @pytest.fixture(scope="session")
# def LiveStrategy_1():
#     yield Contract("0xC1810aa7F733269C39D640f240555d0A4ebF4264")


# use this if your strategy is already deployed
# @pytest.fixture(scope="module")
# def strategy():
#     # parameters for this are: strategy, vault, max deposit, minTimePerInvest, slippage protection (10000 = 100% slippage allowed),
#     strategy = Contract("0xC1810aa7F733269C39D640f240555d0A4ebF4264")
#     yield strategy
