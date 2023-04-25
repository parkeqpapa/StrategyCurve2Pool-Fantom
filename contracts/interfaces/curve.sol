// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.15;
pragma experimental ABIEncoderV2;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

interface IGauge {
    function deposit(uint256) external;

    function balanceOf(address) external view returns (uint256);

    function claim_rewards() external;

    function claimable_tokens(address) external view returns (uint256);

    function claimable_reward(
        address _addressToCheck,
        address _rewardToken
    ) external view returns (uint256);

    function withdraw(uint256) external;
}

interface ICurveFi {
    function get_virtual_price() external view returns (uint256);

    function add_liquidity(
        uint256[2] calldata _amounts,
        uint256 _min_mint_amount
    ) external;

    function remove_liquidity(
        uint256 _amount,
        uint256[2] calldata amounts
    ) external;

    function remove_liquidity_one_coin(
        uint256 _token_amount,
        int128 i,
        uint256 min_amount
    ) external;

    function balances(uint256) external view returns (uint256);

    function get_dy(
        int128 from,
        int128 to,
        uint256 _from_amount
    ) external view returns (uint256);

    function calc_token_amount(
        uint256[2] calldata _amounts,
        bool _is_deposit
    ) external view returns (uint256);

    function calc_withdraw_one_coin(
        uint256 amount,
        int128 i
    ) external view returns (uint256);
}

interface IGaugeFactory {
    function mint(address gauge) external;
}
