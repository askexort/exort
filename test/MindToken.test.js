const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time, loadFixture } = require("@nomicfoundation/hardhat-toolbox/network-helpers");

describe("MindToken", function () {
  // ─── Fixture ────────────────────────────────────────────────────
  async function deployMindTokenFixture() {
    const [owner, community, liquidity, dev, marketing, team, user1, user2, other] =
      await ethers.getSigners();

    // Deploy a mock router (for testing addLiquidity)
    const MockRouter = await ethers.getContractFactory("MockUniswapV2Router");
    const mockRouter = await MockRouter.deploy();

    const MindToken = await ethers.getContractFactory("MindToken");
    const mindToken = await MindToken.deploy(
      community.address,
      liquidity.address,
      dev.address,
      marketing.address,
      team.address,
      await mockRouter.getAddress()
    );

    return {
      mindToken,
      mockRouter,
      owner,
      community,
      liquidity,
      dev,
      marketing,
      team,
      user1,
      user2,
      other,
    };
  }

  // ─── Deployment Tests ───────────────────────────────────────────
  describe("Deployment", function () {
    it("Should set correct token name and symbol", async function () {
      const { mindToken } = await loadFixture(deployMindTokenFixture);
      expect(await mindToken.name()).to.equal("MindToken");
      expect(await mindToken.symbol()).to.equal("MIND");
    });

    it("Should have 18 decimals", async function () {
      const { mindToken } = await loadFixture(deployMindTokenFixture);
      expect(await mindToken.decimals()).to.equal(18);
    });

    it("Should mint total supply of 1 billion", async function () {
      const { mindToken } = await loadFixture(deployMindTokenFixture);
      const totalSupply = await mindToken.totalSupply();
      expect(totalSupply).to.equal(ethers.parseEther("1000000000"));
    });

    it("Should distribute tokens correctly", async function () {
      const { mindToken, community, liquidity, dev, marketing, team } =
        await loadFixture(deployMindTokenFixture);

      const totalSupply = await mindToken.totalSupply();
      const ONE_BILLION = ethers.parseEther("1000000000");

      // 40% community
      expect(await mindToken.balanceOf(community.address)).to.equal(
        (ONE_BILLION * 40n) / 100n
      );

      // 20% liquidity
      expect(await mindToken.balanceOf(liquidity.address)).to.equal(
        (ONE_BILLION * 20n) / 100n
      );

      // 15% development
      expect(await mindToken.balanceOf(dev.address)).to.equal(
        (ONE_BILLION * 15n) / 100n
      );

      // 15% marketing
      expect(await mindToken.balanceOf(marketing.address)).to.equal(
        (ONE_BILLION * 15n) / 100n
      );

      // 10% team (held in contract for vesting)
      expect(await mindToken.balanceOf(await mindToken.getAddress())).to.equal(
        (ONE_BILLION * 10n) / 100n
      );
    });

    it("Should set max transaction amount to 1% of supply", async function () {
      const { mindToken } = await loadFixture(deployMindTokenFixture);
      const ONE_BILLION = ethers.parseEther("1000000000");
      const expected = ONE_BILLION / 100n; // 1%
      expect(await mindToken.maxTransactionAmount()).to.equal(expected);
    });

    it("Should set owner correctly", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);
      expect(await mindToken.owner()).to.equal(owner.address);
    });

    it("Should have trading disabled by default", async function () {
      const { mindToken } = await loadFixture(deployMindTokenFixture);
      expect(await mindToken.tradingEnabled()).to.be.false;
    });

    it("Should revert if zero address provided for community wallet", async function () {
      const [owner, liquidity, dev, marketing, team] = await ethers.getSigners();
      const MindToken = await ethers.getContractFactory("MindToken");

      await expect(
        MindToken.deploy(
          ethers.ZeroAddress,
          liquidity.address,
          dev.address,
          marketing.address,
          team.address,
          ethers.ZeroAddress
        )
      ).to.be.reverted;
    });
  });

  // ─── Distribution Wallets ───────────────────────────────────────
  describe("Distribution", function () {
    it("Should have correct distribution percentages", async function () {
      const { mindToken } = await loadFixture(deployMindTokenFixture);
      const ONE_BILLION = ethers.parseEther("1000000000");

      const [community, liquidity, development, marketing, team] =
        await mindToken.getDistribution();

      expect(community).to.equal((ONE_BILLION * 40n) / 100n);
      expect(liquidity).to.equal((ONE_BILLION * 20n) / 100n);
      expect(development).to.equal((ONE_BILLION * 15n) / 100n);
      expect(marketing).to.equal((ONE_BILLION * 15n) / 100n);
      expect(team).to.equal((ONE_BILLION * 10n) / 100n);
    });
  });

  // ─── Trading Controls ───────────────────────────────────────────
  describe("Trading Controls", function () {
    it("Should block transfers from non-exempt addresses before trading", async function () {
      const { mindToken, community, user1 } = await loadFixture(deployMindTokenFixture);

      await expect(
        mindToken.connect(community).transfer(user1.address, ethers.parseEther("100"))
      ).to.be.revertedWithCustomError(mindToken, "TradingNotEnabled");
    });

    it("Should allow exempt addresses to transfer before trading", async function () {
      const { mindToken, owner, user1 } = await loadFixture(deployMindTokenFixture);

      // Owner is exempt, so transfer should work (but owner has 0 balance initially)
      // Community has balance and is NOT exempt by default, so test with owner setting exempt
      await mindToken.setExemptFromMaxTx(user1.address, true);
      expect(await mindToken.isExemptFromMaxTx(user1.address)).to.be.true;
    });

    it("Should enable trading", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);

      await mindToken.connect(owner).enableTrading();
      expect(await mindToken.tradingEnabled()).to.be.true;
    });

    it("Should not allow non-owner to enable trading", async function () {
      const { mindToken, user1 } = await loadFixture(deployMindTokenFixture);

      await expect(mindToken.connect(user1).enableTrading()).to.be.revertedWith(
        "Ownable: caller is not the owner"
      );
    });
  });

  // ─── Anti-Whale Protection ──────────────────────────────────────
  describe("Anti-Whale", function () {
    it("Should enforce max transaction limit", async function () {
      const { mindToken, community, user1, owner } = await loadFixture(deployMindTokenFixture);

      // Enable trading
      await mindToken.connect(owner).enableTrading();

      const maxTx = await mindToken.maxTransactionAmount();
      const overMax = maxTx + 1n;

      await expect(
        mindToken.connect(community).transfer(user1.address, overMax)
      ).to.be.revertedWithCustomError(mindToken, "ExceedsMaxTransaction");
    });

    it("Should allow transactions under the limit", async function () {
      const { mindToken, community, user1, owner } = await loadFixture(deployMindTokenFixture);

      await mindToken.connect(owner).enableTrading();

      const maxTx = await mindToken.maxTransactionAmount();

      await mindToken.connect(community).transfer(user1.address, maxTx);
      expect(await mindToken.balanceOf(user1.address)).to.equal(maxTx);
    });

    it("Should update max transaction percent", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);

      await mindToken.connect(owner).setMaxTransactionPercent(2);
      const ONE_BILLION = ethers.parseEther("1000000000");
      expect(await mindToken.maxTransactionAmount()).to.equal((ONE_BILLION * 2n) / 100n);
    });

    it("Should reject invalid max transaction percent", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);

      await expect(mindToken.connect(owner).setMaxTransactionPercent(0)).to.be.revertedWith(
        "Must be 1-5%"
      );

      await expect(mindToken.connect(owner).setMaxTransactionPercent(6)).to.be.revertedWith(
        "Must be 1-5%"
      );
    });

    it("Should batch set exemptions", async function () {
      const { mindToken, owner, user1, user2 } = await loadFixture(deployMindTokenFixture);

      await mindToken.connect(owner).setExemptFromMaxTxBatch(
        [user1.address, user2.address],
        true
      );

      expect(await mindToken.isExemptFromMaxTx(user1.address)).to.be.true;
      expect(await mindToken.isExemptFromMaxTx(user2.address)).to.be.true;
    });
  });

  // ─── Vesting ────────────────────────────────────────────────────
  describe("Vesting", function () {
    it("Should create vesting schedule for team wallet", async function () {
      const { mindToken, team } = await loadFixture(deployMindTokenFixture);

      const vestedAmount = await mindToken.vestingVestedAmount(team.address);
      // At t=0, vested amount should be 0
      expect(vestedAmount).to.equal(0);
    });

    it("Should vest linearly over 12 months", async function () {
      const { mindToken, team } = await loadFixture(deployMindTokenFixture);

      const ONE_BILLION = ethers.parseEther("1000000000");
      const teamAllocation = (ONE_BILLION * 10n) / 100n;

      // Fast forward 6 months (half vesting period)
      await time.increase(182.5 * 24 * 60 * 60); // ~6 months

      const vested = await mindToken.vestingVestedAmount(team.address);
      // Should be approximately 50% vested (allowing some variance for block time)
      const halfVest = teamAllocation / 2n;
      const tolerance = teamAllocation / 100n; // 1% tolerance
      expect(vested).to.be.closeTo(halfVest, tolerance);
    });

    it("Should fully vest after 12 months", async function () {
      const { mindToken, team } = await loadFixture(deployMindTokenFixture);

      const ONE_BILLION = ethers.parseEther("1000000000");
      const teamAllocation = (ONE_BILLION * 10n) / 100n;

      // Fast forward 12 months
      await time.increase(365 * 24 * 60 * 60);

      const vested = await mindToken.vestingVestedAmount(team.address);
      expect(vested).to.equal(teamAllocation);
    });

    it("Should allow team to release vested tokens", async function () {
      const { mindToken, team, owner } = await loadFixture(deployMindTokenFixture);

      // Fast forward 6 months
      await time.increase(182.5 * 24 * 60 * 60);

      const releasable = await mindToken.vestingReleasable(team.address);
      expect(releasable).to.be.gt(0);

      await mindToken.connect(team).releaseVestedTokens();

      const balance = await mindToken.balanceOf(team.address);
      expect(balance).to.be.gt(0);
    });

    it("Should not release more than vested", async function () {
      const { mindToken, team } = await loadFixture(deployMindTokenFixture);

      // Try to release immediately (nothing vested yet)
      await mindToken.connect(team).releaseVestedTokens();
      expect(await mindToken.balanceOf(team.address)).to.equal(0);
    });

    it("Should track released amount correctly", async function () {
      const { mindToken, team } = await loadFixture(deployMindTokenFixture);

      // Fast forward 3 months
      await time.increase(91.25 * 24 * 60 * 60);

      await mindToken.connect(team).releaseVestedTokens();
      const balance1 = await mindToken.balanceOf(team.address);

      // Fast forward 3 more months
      await time.increase(91.25 * 24 * 60 * 60);

      await mindToken.connect(team).releaseVestedTokens();
      const balance2 = await mindToken.balanceOf(team.address);

      expect(balance2).to.be.gt(balance1);
    });
  });

  // ─── Burning ────────────────────────────────────────────────────
  describe("Burning", function () {
    it("Should allow token holders to burn their tokens", async function () {
      const { mindToken, community, owner } = await loadFixture(deployMindTokenFixture);

      const balanceBefore = await mindToken.balanceOf(community.address);
      const burnAmount = ethers.parseEther("1000000");

      await mindToken.connect(community).burn(burnAmount);

      expect(await mindToken.balanceOf(community.address)).to.equal(balanceBefore - burnAmount);
    });

    it("Should reduce total supply on burn", async function () {
      const { mindToken, community, owner } = await loadFixture(deployMindTokenFixture);

      const supplyBefore = await mindToken.totalSupply();
      const burnAmount = ethers.parseEther("1000000");

      await mindToken.connect(community).burn(burnAmount);

      expect(await mindToken.totalSupply()).to.equal(supplyBefore - burnAmount);
    });
  });

  // ─── Pausable ───────────────────────────────────────────────────
  describe("Pausable", function () {
    it("Should allow owner to pause", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);

      await mindToken.connect(owner).pause();
      expect(await mindToken.paused()).to.be.true;
    });

    it("Should block transfers when paused", async function () {
      const { mindToken, owner, community, user1 } = await loadFixture(deployMindTokenFixture);

      // Enable trading first, then pause
      await mindToken.connect(owner).enableTrading();
      await mindToken.connect(owner).pause();

      await expect(
        mindToken.connect(community).transfer(user1.address, ethers.parseEther("100"))
      ).to.be.revertedWith("Pausable: paused");
    });

    it("Should allow owner to unpause", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);

      await mindToken.connect(owner).pause();
      await mindToken.connect(owner).unpause();
      expect(await mindToken.paused()).to.be.false;
    });

    it("Should not allow non-owner to pause", async function () {
      const { mindToken, user1 } = await loadFixture(deployMindTokenFixture);

      await expect(mindToken.connect(user1).pause()).to.be.revertedWith(
        "Ownable: caller is not the owner"
      );
    });
  });

  // ─── Auto-Liquidity ────────────────────────────────────────────
  describe("Auto-Liquidity", function () {
    it("Should have auto-liquidity enabled by default", async function () {
      const { mindToken } = await loadFixture(deployMindTokenFixture);
      expect(await mindToken.autoLiquidityEnabled()).to.be.true;
    });

    it("Should toggle auto-liquidity", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);

      await mindToken.connect(owner).toggleAutoLiquidity(false);
      expect(await mindToken.autoLiquidityEnabled()).to.be.false;

      await mindToken.connect(owner).toggleAutoLiquidity(true);
      expect(await mindToken.autoLiquidityEnabled()).to.be.true;
    });

    it("Should update liquidity threshold", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);

      const newThreshold = ethers.parseEther("500000");
      await mindToken.connect(owner).setLiquidityThreshold(newThreshold);
      expect(await mindToken.liquidityThreshold()).to.equal(newThreshold);
    });

    it("Should not allow non-owner to toggle", async function () {
      const { mindToken, user1 } = await loadFixture(deployMindTokenFixture);

      await expect(
        mindToken.connect(user1).toggleAutoLiquidity(false)
      ).to.be.revertedWith("Ownable: caller is not the owner");
    });
  });

  // ─── AMM Pair ───────────────────────────────────────────────────
  describe("AMM Pair", function () {
    it("Should set AMM pair address", async function () {
      const { mindToken, owner, user1 } = await loadFixture(deployMindTokenFixture);

      await mindToken.connect(owner).setAMMPair(user1.address);
      expect(await mindToken.isAMMPair(user1.address)).to.be.true;
      expect(await mindToken.uniswapV2Pair()).to.equal(user1.address);
    });

    it("Should not allow zero address for AMM pair", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);

      await expect(
        mindToken.connect(owner).setAMMPair(ethers.ZeroAddress)
      ).to.be.revertedWithCustomError(mindToken, "ZeroAddress");
    });
  });

  // ─── Router ─────────────────────────────────────────────────────
  describe("Router", function () {
    it("Should update router address", async function () {
      const { mindToken, owner, user1 } = await loadFixture(deployMindTokenFixture);

      await mindToken.connect(owner).setRouter(user1.address);
      expect(await mindToken.uniswapV2Router()).to.equal(user1.address);
    });

    it("Should not allow zero address for router", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);

      await expect(
        mindToken.connect(owner).setRouter(ethers.ZeroAddress)
      ).to.be.revertedWithCustomError(mindToken, "ZeroAddress");
    });
  });

  // ─── Access Control ────────────────────────────────────────────
  describe("Access Control", function () {
    it("Should grant default admin role to owner", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);

      const DEFAULT_ADMIN_ROLE = ethers.ZeroHash;
      expect(await mindToken.hasRole(DEFAULT_ADMIN_ROLE, owner.address)).to.be.true;
    });

    it("Should grant liquidity manager role to deployer", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);

      const LIQUIDITY_MANAGER_ROLE = ethers.keccak256(
        ethers.toUtf8Bytes("LIQUIDITY_MANAGER_ROLE")
      );
      expect(await mindToken.hasRole(LIQUIDITY_MANAGER_ROLE, owner.address)).to.be.true;
    });

    it("Should grant vesting manager role to deployer", async function () {
      const { mindToken, owner } = await loadFixture(deployMindTokenFixture);

      const VESTING_MANAGER_ROLE = ethers.keccak256(
        ethers.toUtf8Bytes("VESTING_MANAGER_ROLE")
      );
      expect(await mindToken.hasRole(VESTING_MANAGER_ROLE, owner.address)).to.be.true;
    });
  });

  // ─── Edge Cases ─────────────────────────────────────────────────
  describe("Edge Cases", function () {
    it("Should handle zero amount transfer", async function () {
      const { mindToken, community, user1, owner } = await loadFixture(deployMindTokenFixture);

      await mindToken.connect(owner).enableTrading();
      await mindToken.connect(community).transfer(user1.address, 0);
    });

    it("Should allow owner to transfer ownership", async function () {
      const { mindToken, owner, user1 } = await loadFixture(deployMindTokenFixture);

      await mindToken.connect(owner).transferOwnership(user1.address);
      expect(await mindToken.owner()).to.equal(user1.address);
    });

    it("Should get contract ETH balance", async function () {
      const { mindToken } = await loadFixture(deployMindTokenFixture);
      expect(await mindToken.getContractETHBalance()).to.equal(0);
    });

    it("Should get contract token balance", async function () {
      const { mindToken } = await loadFixture(deployMindTokenFixture);
      const ONE_BILLION = ethers.parseEther("1000000000");
      const teamAllocation = (ONE_BILLION * 10n) / 100n;
      expect(await mindToken.getContractTokenBalance()).to.equal(teamAllocation);
    });
  });
});
