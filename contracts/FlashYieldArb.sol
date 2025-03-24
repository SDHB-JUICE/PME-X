// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@aave/core-v3/contracts/flashloan/base/FlashLoanReceiverBase.sol";
import "@aave/core-v3/contracts/interfaces/IPoolAddressesProvider.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title FlashYieldArb
 * @dev Contract for executing flash loan arbitrage and yield farming
 */
contract FlashYieldArb is FlashLoanReceiverBase, Ownable {
    struct ArbitrageParams {
        address dex1;
        address dex2;
        bytes dex1Data;
        bytes dex2Data;
        uint256 minProfit;
    }

    event ArbitrageExecuted(
        address[] tokens,
        uint256[] amounts,
        uint256[] premiums,
        uint256 profit
    );

    event FlashLoanFailed(
        address[] tokens,
        uint256[] amounts,
        string reason
    );

    event TokensRescued(
        address token,
        uint256 amount
    );

    /**
     * @dev Constructor
     * @param provider The address of the Aave PoolAddressesProvider contract
     */
    constructor(IPoolAddressesProvider provider) FlashLoanReceiverBase(provider) {}

    /**
     * @dev Executes arbitrage using flash loan
     * @param token The address of the token to borrow
     * @param amount The amount to borrow
     * @param dex1 The address of the first DEX router
     * @param dex2 The address of the second DEX router
     * @param dex1Data The calldata for the first DEX
     * @param dex2Data The calldata for the second DEX
     * @param minProfit The minimum profit required for the arbitrage to execute
     */
    function executeArbitrage(
        address token,
        uint256 amount,
        address dex1,
        address dex2,
        bytes calldata dex1Data,
        bytes calldata dex2Data,
        uint256 minProfit
    ) external onlyOwner {
        address[] memory assets = new address[](1);
        assets[0] = token;
        
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = amount;
        
        uint256[] memory modes = new uint256[](1);
        modes[0] = 0; // 0 = no debt, 1 = stable, 2 = variable
        
        // Store arbitrage parameters for executeOperation
        ArbitrageParams memory params = ArbitrageParams({
            dex1: dex1,
            dex2: dex2,
            dex1Data: dex1Data,
            dex2Data: dex2Data,
            minProfit: minProfit
        });
        
        bytes memory paramsData = abi.encode(params);
        
        // Execute flash loan
        try POOL.flashLoan(
            address(this),
            assets,
            amounts,
            modes,
            address(this),
            paramsData,
            0
        ) {
            // Flash loan executed successfully
        } catch Error(string memory reason) {
            emit FlashLoanFailed(assets, amounts, reason);
        } catch (bytes memory) {
            emit FlashLoanFailed(assets, amounts, "Unknown error");
        }
    }

    /**
     * @dev Executes arbitrage after receiving flash loan
     * @param assets The addresses of the assets being flash-borrowed
     * @param amounts The amounts of the assets being flash-borrowed
     * @param premiums The fee to be paid for each asset
     * @param initiator The address of the flashloan initiator
     * @param params The arbitrary data passed by the initiator
     * @return success Whether the execution was successful or not
     */
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        // Ensure only the lending pool can call this
        require(msg.sender == address(POOL), "FlashYieldArb: Caller must be lending pool");
        
        // Decode arbitrage parameters
        ArbitrageParams memory arbParams = abi.decode(params, (ArbitrageParams));
        
        // Get initial balance to calculate profit
        uint256 initialBalance = IERC20(assets[0]).balanceOf(address(this));
        
        // Execute trades on DEXes
        // Trade 1: Buy low on DEX 1
        (bool success1, ) = arbParams.dex1.call(arbParams.dex1Data);
        require(success1, "FlashYieldArb: DEX 1 trade failed");
        
        // Trade 2: Sell high on DEX 2
        (bool success2, ) = arbParams.dex2.call(arbParams.dex2Data);
        require(success2, "FlashYieldArb: DEX 2 trade failed");
        
        // Calculate profit
        uint256 finalBalance = IERC20(assets[0]).balanceOf(address(this));
        uint256 totalOwed = amounts[0] + premiums[0];
        
        // Ensure we have enough profit
        require(finalBalance >= totalOwed, "FlashYieldArb: Insufficient funds to repay flash loan");
        
        uint256 profit = finalBalance - totalOwed;
        require(profit >= arbParams.minProfit, "FlashYieldArb: Profit below minimum threshold");
        
        // Approve repayment of the loan plus fee
        for (uint i = 0; i < assets.length; i++) {
            uint amountOwed = amounts[i] + premiums[i];
            IERC20(assets[i]).approve(address(POOL), amountOwed);
        }
        
        // Emit event
        emit ArbitrageExecuted(assets, amounts, premiums, profit);
        
        return true;
    }

    /**
     * @dev Withdraws profits to owner
     * @param tokens Array of token addresses to withdraw
     */
    function withdrawProfits(address[] calldata tokens) external onlyOwner {
        for (uint i = 0; i < tokens.length; i++) {
            address token = tokens[i];
            uint256 balance;
            
            if (token == address(0)) {
                // ETH
                balance = address(this).balance;
                if (balance > 0) {
                    (bool success, ) = owner().call{value: balance}("");
                    require(success, "FlashYieldArb: ETH transfer failed");
                }
            } else {
                // ERC20 token
                balance = IERC20(token).balanceOf(address(this));
                if (balance > 0) {
                    IERC20(token).transfer(owner(), balance);
                }
            }
        }
    }
    
    /**
     * @dev Rescues tokens mistakenly sent to the contract
     * @param token The address of the token to rescue
     */
    function rescueTokens(address token) external onlyOwner {
        uint256 balance;
        
        if (token == address(0)) {
            // ETH
            balance = address(this).balance;
            require(balance > 0, "FlashYieldArb: No ETH to rescue");
            (bool success, ) = owner().call{value: balance}("");
            require(success, "FlashYieldArb: ETH transfer failed");
        } else {
            // ERC20 token
            balance = IERC20(token).balanceOf(address(this));
            require(balance > 0, "FlashYieldArb: No tokens to rescue");
            IERC20(token).transfer(owner(), balance);
        }
        
        emit TokensRescued(token, balance);
    }
    
    /**
     * @dev Allows the contract to receive ETH
     */
    receive() external payable {}
}