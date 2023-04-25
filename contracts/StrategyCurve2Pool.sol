// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.15;
pragma experimental ABIEncoderV2;

import { BaseStrategy, StrategyParams } from "@yearnvaults/contracts/BaseStrategy.sol";
import { ICurveFi, IGauge, IGaugeFactory } from "./interfaces/curve.sol";
import { IUniswapV2Router02 } from "./interfaces/uniswap.sol";
import { SafeERC20, IERC20, Address } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";

// These are the core Yearn libraries
abstract contract StrategyCurveBase is BaseStrategy {
    using Address for address;
    using SafeMath for uint256;
    using SafeERC20 for IERC20;

    /* ========== STATE VARIABLES ========== */
    // these should stay the same across different wants.

    // curve infrastructure contracts
    IGauge public constant gauge =
        IGauge(0x15bB164F9827De760174d3d3dAD6816eF50dE13c);
    // Swap stuff

    IERC20 internal constant crv =
        IERC20(0x1E4F97b9f9F913c46F1632781732927B9019C68b);
    IERC20 internal constant wftm =
        IERC20(0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83);

    /* ========== CONSTRUCTOR ========== */

    constructor(address _vault) BaseStrategy(_vault) {}

    /* ========== VIEWS ========== */

    function name() external view override returns (string memory) {
        return "StrategyCurve2Pool";
    }

    ///@notice How much want we have staked in Curve's gauge
    function stakedBalance() public view returns (uint256) {
        return gauge.balanceOf(address(this));
    }

    ///@notice Balance of want sitting in our strategy
    function balanceOfWant() public view returns (uint256) {
        return want.balanceOf(address(this));
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        return balanceOfWant().add(stakedBalance());
    }

    /* ========== MUTATIVE FUNCTIONS ========== */

    function adjustPosition(uint256 _debtOutstanding) internal override {
        if (emergencyExit) {
            return;
        }
        // Send all of our LP tokens to the proxy and deposit to the gauge if we have any
        uint256 _toInvest = balanceOfWant();
        if (_toInvest > 0) {
            gauge.deposit(_toInvest);
        }
    }

    function liquidatePosition(
        uint256 _amountNeeded
    ) internal override returns (uint256 _liquidatedAmount, uint256 _loss) {
        uint256 _wantBal = balanceOfWant();
        if (_amountNeeded > _wantBal) {
            // check if we have enough free funds to cover the withdrawal
            uint256 _stakedBal = stakedBalance();
            if (_stakedBal > 0) {
                gauge.withdraw(
                    Math.min(_stakedBal, _amountNeeded.sub(_wantBal))
                );
            }
            uint256 _withdrawnBal = balanceOfWant();
            _liquidatedAmount = Math.min(_amountNeeded, _withdrawnBal);
            _loss = _amountNeeded.sub(_liquidatedAmount);
        } else {
            // we have enough balance to cover the liquidation available
            return (_amountNeeded, 0);
        }
    }

    // fire sale, get rid of it all!
    function liquidateAllPositions() internal override returns (uint256) {
        uint256 _stakedBal = stakedBalance();
        if (_stakedBal > 0) {
            // don't bother withdrawing zero
            gauge.withdraw(_stakedBal);
        }
        return balanceOfWant();
    }

    function protectedTokens()
        internal
        view
        override
        returns (address[] memory)
    {}

    /* ========== SETTERS ========== */

    // These functions are useful for setting parameters of the strategy that may need to be adjusted.
}

contract StrategyCurve2Pool is StrategyCurveBase {
    /* ========== STATE VARIABLES ========== */
    // these will likely change across different wants.
    using SafeMath for uint256;

    // Curve stuff
    ICurveFi internal constant curve =
        ICurveFi(0x27E611FD27b276ACbd5Ffd632E5eAEBEC9761E40); // this is used for depositing to all 3Crv metapools

    IGaugeFactory internal constant gaugeFactory =
        IGaugeFactory(0xabC000d88f23Bb45525E447528DBF656A9D55bf5);
    // we use these to deposit to our curve pool
    address public targetStable; ///@notice This is the stablecoin we are using to take profits and deposit into 3Crv.
    address internal constant spooky =
        0xF491e7B69E4244ad4002BC14e878a34207E38c29; // we use this to sell our bonus token

    IERC20 internal constant usdc =
        IERC20(0x04068DA6C83AFCFA0e13ba15A6696662335D5B75);
    IERC20 internal constant dai =
        IERC20(0x8D11eC38a3EB5E956B052f67Da8Bdc9bef8Abf3E);

    /* ========== CONSTRUCTOR ========== */

    constructor(address _vault) StrategyCurveBase(_vault) {
        maxReportDelay = 100 days; // 100 days in seconds
        minReportDelay = 21 days; // 21 days in seconds
        creditThreshold = 1e6 * 1e18;

        // these are our standard approvals. want = Curve LP token
        want.approve(address(gauge), type(uint256).max);
        crv.approve(address(spooky), type(uint256).max);
        wftm.approve(address(spooky), type(uint256).max);

        // these are our approvals and path specific to this contract
        dai.approve(address(curve), type(uint256).max);
        usdc.approve(address(curve), type(uint256).max);

        // start with usdt
        targetStable = address(dai);
    }

    /* ========== MUTATIVE FUNCTIONS ========== */

    function prepareReturn(
        uint256 _debtOutstanding
    )
        internal
        override
        returns (uint256 _profit, uint256 _loss, uint256 _debtPayment)
    {
        // if we have anything in the gauge, then harvest CRV from the gauge
        gaugeFactory.mint(address(gauge));
        uint256 _crvBal = crv.balanceOf(address(this));
        if (_crvBal > 0) {
            _sellToken(address(crv), _crvBal);
        }

        uint256 usdcBal = usdc.balanceOf(address(this));
        uint256 daiBal = dai.balanceOf(address(this));
        if (usdcBal > 0 || daiBal > 0) {
            curve.add_liquidity([usdcBal, daiBal], 0);
        }

        uint256 stakedBal = stakedBalance();
        if (_debtOutstanding > 0) {
            if (stakedBal > 0) {
                gauge.withdraw(Math.min(stakedBal, _debtOutstanding));
            }
            uint256 withdrawnBal = balanceOfWant();
            _debtPayment = Math.min(stakedBal, _debtOutstanding);
        }
        uint256 assets = estimatedTotalAssets();
        uint256 debt = vault.strategies(address(this)).totalDebt;

        if (assets > debt) {
            _profit = assets.sub(debt);
            uint256 _wantBal = balanceOfWant();
            if (_profit.add(_debtPayment) > _wantBal) {
                liquidateAllPositions();
            }
        } else {
            _loss = debt.sub(assets);
        } // we're done harvesting, so reset our trigger if we used it
        forceHarvestTriggerOnce = false;
    }

    function prepareMigration(address _newStrategy) internal override {
        uint256 _stakedBal = stakedBalance();
        if (_stakedBal > 0) {
            gauge.withdraw(_stakedBal);
        }
    }

    function _sellToken(address token, uint256 amount) internal {
        address[] memory path = new address[](3);
        path[0] = address(token);
        path[1] = address(wftm);
        path[2] = address(targetStable);
        IUniswapV2Router02(spooky).swapExactTokensForTokens(
            amount,
            uint256(0),
            path,
            address(this),
            block.timestamp
        );
    }

    // Sells our harvested CRV into the selected output, then WETH -> stables together with any WETH from rewards on UniV3
    /* ========== KEEP3RS ========== */
    // use this to determine when to harvest
    function harvestTrigger(
        uint256 callCostinEth
    ) public view override returns (bool) {
        // Should not trigger if strategy is not active (no assets and no debtRatio). This means we don't need to adjust keeper job.
        if (!isActive()) {
            return false;
        }

        StrategyParams memory params = vault.strategies(address(this));
        // harvest no matter what once we reach our maxDelay
        if (block.timestamp.sub(params.lastReport) > maxReportDelay) {
            return true;
        }

        // check if the base fee gas price is higher than we allow. if it is, block harvests.
        if (!isBaseFeeAcceptable()) {
            return false;
        }

        // trigger if we want to manually harvest, but only if our gas price is acceptable
        if (forceHarvestTriggerOnce) {
            return true;
        }

        // harvest if we hit our minDelay, but only if our gas price is acceptable
        if (block.timestamp.sub(params.lastReport) > minReportDelay) {
            return true;
        }

        // harvest our credit if it's above our threshold
        if (vault.creditAvailable() > creditThreshold) {
            return true;
        }

        // otherwise, we don't harvest
        return false;
    }

    // convert our keeper's eth cost into want, we don't need this anymore since we don't use baseStrategy harvestTrigger
    function ethToWant(
        uint256 _ethAmount
    ) public view override returns (uint256) {}

    /* ========== SETTERS ========== */

    // These functions are useful for setting parameters of the strategy that may need to be adjusted.

    ///@notice Set optimal token to sell harvested funds for depositing to Curve.
    function setOptimal(uint256 _optimal) external onlyVaultManagers {
        if (_optimal == 0) {
            targetStable = address(dai);
        } else if (_optimal == 1) {
            targetStable = address(usdc);
        } else {
            revert("incorrect token");
        }
    }
}
