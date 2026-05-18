// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title IUniswapV2Router02 (minimal interface)
 */
interface IUniswapV2Router02 {
    function factory() external pure returns (address);
    function WETH() external pure returns (address);
    function swapExactTokensForETHSupportingFeeOnTransferTokens(
        uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline
    ) external;
    function addLiquidityETH(
        address token, uint amountTokenDesired, uint amountTokenMin, uint amountETHMin, address to, uint deadline
    ) external payable returns (uint amountToken, uint amountETH, uint liquidity);
}

interface IUniswapV2Factory {
    function getPair(address tokenA, address tokenB) external view returns (address pair);
}

/**
 * @title MindToken (MIND)
 * @notice ERC-20 token for the OpenMind ecosystem on Base chain
 * @dev Features: burnable, pausable, anti-whale, vesting, auto-liquidity
 */
contract MindToken is ERC20, ERC20Burnable, ERC20Permit, Ownable, AccessControl, Pausable {
    // ─── Roles ────────────────────────────────────────────────────
    bytes32 public constant LIQUIDITY_MANAGER_ROLE = keccak256("LIQUIDITY_MANAGER_ROLE");
    bytes32 public constant VESTING_MANAGER_ROLE = keccak256("VESTING_MANAGER_ROLE");

    // ─── Constants ────────────────────────────────────────────────
    uint256 public constant TOTAL_SUPPLY = 1_000_000_000 * 1e18;
    uint256 public constant MAX_TX_PERCENT = 1;
    uint256 public constant LIQUIDITY_FEE_BPS = 200;
    uint256 public constant BPS_DENOMINATOR = 10_000;

    // ─── Distribution Wallets ─────────────────────────────────────
    address public communityWallet;
    address public liquidityPool;
    address public developmentWallet;
    address public marketingWallet;
    address public teamWallet;

    // ─── Anti-Whale ───────────────────────────────────────────────
    uint256 public maxTransactionAmount;
    mapping(address => bool) public isExemptFromMaxTx;

    // ─── Vesting ──────────────────────────────────────────────────
    struct VestingSchedule {
        uint256 totalAmount;
        uint256 startTime;
        uint256 duration;
        uint256 released;
        bool exists;
    }

    mapping(address => VestingSchedule) public vestingSchedules;
    uint256 public vestingDuration = 365 days;

    // ─── Auto-Liquidity ───────────────────────────────────────────
    IUniswapV2Router02 public uniswapV2Router;
    address public uniswapV2Pair;
    bool public autoLiquidityEnabled = true;
    uint256 public liquidityThreshold = 1_000_000 * 1e18;
    uint256 public liquidityAccumulated;

    // ─── Trading ──────────────────────────────────────────────────
    bool public tradingEnabled = false;
    mapping(address => bool) public isAMMPair;

    // ─── Events ───────────────────────────────────────────────────
    event TradingEnabled(uint256 timestamp);
    event AutoLiquidity(uint256 tokensSwapped, uint256 ethAdded, uint256 tokensAdded);
    event VestingCreated(address indexed beneficiary, uint256 amount, uint256 duration);
    event VestingReleased(address indexed beneficiary, uint256 amount);
    event MaxTransactionAmountUpdated(uint256 amount);
    event AutoLiquidityToggled(bool enabled);

    // ─── Errors ───────────────────────────────────────────────────
    error ExceedsMaxTransaction(uint256 amount, uint256 maxAmount);
    error TradingNotEnabled();

    // ─── Constructor ──────────────────────────────────────────────
    constructor(
        address _communityWallet,
        address _liquidityPool,
        address _developmentWallet,
        address _marketingWallet,
        address _teamWallet,
        address _routerAddress
    )
        ERC20("MindToken", "MIND")
        ERC20Permit("MindToken")
        Ownable(msg.sender)
    {
        require(
            _communityWallet != address(0) && _liquidityPool != address(0) &&
            _developmentWallet != address(0) && _marketingWallet != address(0) &&
            _teamWallet != address(0) && _routerAddress != address(0),
            "Zero address"
        );

        communityWallet = _communityWallet;
        liquidityPool = _liquidityPool;
        developmentWallet = _developmentWallet;
        marketingWallet = _marketingWallet;
        teamWallet = _teamWallet;

        uniswapV2Router = IUniswapV2Router02(_routerAddress);
        uniswapV2Pair = IUniswapV2Factory(uniswapV2Router.factory())
            .getPair(address(this), uniswapV2Router.WETH());

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(LIQUIDITY_MANAGER_ROLE, msg.sender);
        _grantRole(VESTING_MANAGER_ROLE, msg.sender);

        isExemptFromMaxTx[msg.sender] = true;
        isExemptFromMaxTx[address(this)] = true;
        isExemptFromMaxTx[_communityWallet] = true;
        isExemptFromMaxTx[_liquidityPool] = true;
        isExemptFromMaxTx[_developmentWallet] = true;
        isExemptFromMaxTx[_marketingWallet] = true;

        maxTransactionAmount = (TOTAL_SUPPLY * MAX_TX_PERCENT) / 100;

        // Distribute: 40% community, 20% LP, 15% dev, 15% marketing, 10% team
        _mint(_communityWallet, TOTAL_SUPPLY * 40 / 100);
        _mint(_liquidityPool, TOTAL_SUPPLY * 20 / 100);
        _mint(_developmentWallet, TOTAL_SUPPLY * 15 / 100);
        _mint(_marketingWallet, TOTAL_SUPPLY * 15 / 100);

        uint256 teamAmount = TOTAL_SUPPLY * 10 / 100;
        _mint(address(this), teamAmount);
        vestingSchedules[_teamWallet] = VestingSchedule({
            totalAmount: teamAmount,
            startTime: block.timestamp,
            duration: vestingDuration,
            released: 0,
            exists: true
        });

        if (uniswapV2Pair != address(0)) {
            isAMMPair[uniswapV2Pair] = true;
            isExemptFromMaxTx[uniswapV2Pair] = true;
        }
    }

    // ─── Core Overrides ──────────────────────────────────────────

    function _update(address from, address to, uint256 value)
        internal
        override(ERC20)
    {
        super._update(from, to, value);
    }

    // ─── Transfer Hook (anti-whale + auto-liquidity) ─────────────

    function transfer(address to, uint256 amount)
        public
        override
        returns (bool)
    {
        _checkTradingEnabled();
        _checkAntiWhale(amount);
        _handleFeeAndTransfer(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount)
        public
        override
        returns (bool)
    {
        _checkTradingEnabled();
        _checkAntiWhale(amount);

        uint256 currentAllowance = allowance(from, msg.sender);
        if (currentAllowance != type(uint256).max) {
            require(currentAllowance >= amount, "ERC20: insufficient allowance");
            unchecked {
                _approve(from, msg.sender, currentAllowance - amount);
            }
        }

        _handleFeeAndTransfer(from, to, amount);
        return true;
    }

    // ─── Internal Helpers ─────────────────────────────────────────

    function _checkTradingEnabled() internal view {
        if (!tradingEnabled && !isExemptFromMaxTx[msg.sender] && !isAMMPair[msg.sender]) {
            revert TradingNotEnabled();
        }
    }

    function _checkAntiWhale(uint256 amount) internal view {
        if (!isExemptFromMaxTx[msg.sender] && !isExemptFromMaxTx[tx.origin]) {
            require(amount <= maxTransactionAmount, "Exceeds max transaction");
        }
    }

    function _handleFeeAndTransfer(address from, address to, uint256 amount) internal {
        if (autoLiquidityEnabled && isAMMPair[to] && !isExemptFromMaxTx[from]) {
            uint256 feeAmount = (amount * LIQUIDITY_FEE_BPS) / BPS_DENOMINATOR;
            uint256 transferAmount = amount - feeAmount;
            super._transfer(from, address(this), feeAmount);
            super._transfer(from, to, transferAmount);
            liquidityAccumulated += feeAmount;
            if (liquidityAccumulated >= liquidityThreshold) {
                _addLiquidity();
            }
        } else {
            super._transfer(from, to, amount);
        }
    }

    // ─── Trading Controls ─────────────────────────────────────────

    function enableTrading() external onlyOwner {
        tradingEnabled = true;
        emit TradingEnabled(block.timestamp);
    }

    function setMaxTransactionAmount(uint256 _amount) external onlyOwner {
        maxTransactionAmount = _amount;
        emit MaxTransactionAmountUpdated(_amount);
    }

    function setExemptFromMaxTx(address _addr, bool _exempt) external onlyOwner {
        isExemptFromMaxTx[_addr] = _exempt;
    }

    function setAMMPair(address _pair, bool _isAMM) external onlyOwner {
        isAMMPair[_pair] = _isAMM;
        isExemptFromMaxTx[_pair] = _isAMM;
    }

    // ─── Pause ────────────────────────────────────────────────────

    function pause() external onlyOwner { _pause(); }
    function unpause() external onlyOwner { _unpause(); }

    // ─── Auto-Liquidity ───────────────────────────────────────────

    function _addLiquidity() internal {
        if (liquidityAccumulated == 0) return;
        uint256 tokenAmount = liquidityAccumulated;
        liquidityAccumulated = 0;

        uint256 halfAmount = tokenAmount / 2;
        uint256 otherHalf = tokenAmount - halfAmount;

        address[] memory path = new address[](2);
        path[0] = address(this);
        path[1] = uniswapV2Router.WETH();

        _approve(address(this), address(uniswapV2Router), halfAmount);
        try uniswapV2Router.swapExactTokensForETHSupportingFeeOnTransferTokens(
            halfAmount, 0, path, address(this), block.timestamp + 300
        ) {} catch {}

        uint256 ethBalance = address(this).balance;
        if (ethBalance > 0 && otherHalf > 0) {
            _approve(address(this), address(uniswapV2Router), otherHalf);
            try uniswapV2Router.addLiquidityETH{value: ethBalance}(
                address(this), otherHalf, 0, 0, liquidityPool, block.timestamp + 300
            ) {} catch {}
        }
    }

    function toggleAutoLiquidity(bool _enabled) external onlyOwner {
        autoLiquidityEnabled = _enabled;
        emit AutoLiquidityToggled(_enabled);
    }

    function setLiquidityThreshold(uint256 _threshold) external onlyOwner {
        liquidityThreshold = _threshold;
    }

    // ─── Vesting ──────────────────────────────────────────────────

    function createVestingSchedule(address _beneficiary, uint256 _amount, uint256 _duration)
        external onlyRole(VESTING_MANAGER_ROLE)
    {
        require(_beneficiary != address(0) && _amount > 0, "Invalid");
        require(!vestingSchedules[_beneficiary].exists, "Exists");

        vestingSchedules[_beneficiary] = VestingSchedule({
            totalAmount: _amount,
            startTime: block.timestamp,
            duration: _duration,
            released: 0,
            exists: true
        });
        emit VestingCreated(_beneficiary, _amount, _duration);
    }

    function releaseVestedTokens() external {
        VestingSchedule storage schedule = vestingSchedules[msg.sender];
        require(schedule.exists, "No schedule");

        uint256 vested = _computeVestedAmount(schedule);
        uint256 releasable = vested - schedule.released;
        require(releasable > 0, "Nothing to release");

        schedule.released += releasable;
        _transfer(address(this), msg.sender, releasable);
        emit VestingReleased(msg.sender, releasable);
    }

    function _computeVestedAmount(VestingSchedule memory s) internal view returns (uint256) {
        if (block.timestamp >= s.startTime + s.duration) return s.totalAmount;
        return (s.totalAmount * (block.timestamp - s.startTime)) / s.duration;
    }

    function getVestedAmount(address _b) external view returns (uint256) {
        VestingSchedule storage s = vestingSchedules[_b];
        return s.exists ? _computeVestedAmount(s) : 0;
    }

    function getReleasableAmount(address _b) external view returns (uint256) {
        VestingSchedule storage s = vestingSchedules[_b];
        if (!s.exists) return 0;
        return _computeVestedAmount(s) - s.released;
    }

    // ─── Wallet Management ────────────────────────────────────────

    function setCommunityWallet(address _w) external onlyOwner { require(_w != address(0)); communityWallet = _w; }
    function setDevelopmentWallet(address _w) external onlyOwner { require(_w != address(0)); developmentWallet = _w; }
    function setMarketingWallet(address _w) external onlyOwner { require(_w != address(0)); marketingWallet = _w; }

    receive() external payable {}
}
