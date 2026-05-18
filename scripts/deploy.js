const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();

  console.log("Deploying MindToken with account:", deployer.address);
  console.log("Account balance:", (await ethers.provider.getBalance(deployer.address)).toString());

  // Network-specific configuration
  const network = await ethers.provider.getNetwork();
  console.log("Network:", network.name, "Chain ID:", network.chainId);

  // Uniswap V2 Router addresses
  const ROUTERS = {
    base: "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24",       // Base mainnet UniswapV2Router
    baseSepolia: "0x...", // Base Sepolia testnet (update when available)
  };

  const routerAddress = ROUTERS[network.name] || ROUTERS.base;

  // Distribution wallets — replace with real addresses in .env
  const communityWallet = process.env.COMMUNITY_WALLET || deployer.address;
  const liquidityPool = process.env.LIQUIDITY_POOL || deployer.address;
  const developmentWallet = process.env.DEVELOPMENT_WALLET || deployer.address;
  const marketingWallet = process.env.MARKETING_WALLET || deployer.address;
  const teamWallet = process.env.TEAM_WALLET || deployer.address;

  console.log("\n── Distribution Wallets ──────────────────────────");
  console.log("Community (40%): ", communityWallet);
  console.log("Liquidity (20%): ", liquidityPool);
  console.log("Development (15%):", developmentWallet);
  console.log("Marketing (15%):  ", marketingWallet);
  console.log("Team (10%):       ", teamWallet);
  console.log("Router:           ", routerAddress);
  console.log("─────────────────────────────────────────────────\n");

  // Deploy
  const MindToken = await ethers.getContractFactory("MindToken");
  const mindToken = await MindToken.deploy(
    communityWallet,
    liquidityPool,
    developmentWallet,
    marketingWallet,
    teamWallet,
    routerAddress
  );

  await mindToken.waitForDeployment();
  const contractAddress = await mindToken.getAddress();

  console.log("MindToken deployed to:", contractAddress);

  // Wait for block confirmations before verification
  if (network.name !== "hardhat" && network.name !== "localhost") {
    console.log("Waiting for block confirmations...");
    await mindToken.deploymentTransaction().wait(5);

    // Verify on Basescan
    console.log("\nVerifying contract on Basescan...");
    try {
      await hre.run("verify:verify", {
        address: contractAddress,
        constructorArguments: [
          communityWallet,
          liquidityPool,
          developmentWallet,
          marketingWallet,
          teamWallet,
          routerAddress,
        ],
      });
      console.log("Contract verified successfully!");
    } catch (error) {
      console.log("Verification failed:", error.message);
      console.log("Try manual verification:");
      console.log(
        `npx hardhat verify --network ${network.name} ${contractAddress} "${communityWallet}" "${liquidityPool}" "${developmentWallet}" "${marketingWallet}" "${teamWallet}" "${routerAddress}"`
      );
    }
  }

  // Post-deployment configuration
  console.log("\n── Post-Deployment ───────────────────────────────");
  console.log("Token Name:     ", await mindToken.name());
  console.log("Token Symbol:   ", await mindToken.symbol());
  console.log("Total Supply:   ", ethers.formatEther(await mindToken.totalSupply()), "MIND");
  console.log("Max Tx Amount:  ", ethers.formatEther(await mindToken.maxTransactionAmount()), "MIND");
  console.log("Owner:          ", await mindToken.owner());
  console.log("──────────────────────────────────────────────────\n");

  console.log("── Next Steps ────────────────────────────────────");
  console.log("1. Add liquidity on Uniswap/BaseSwap");
  console.log("2. Call setAMMPair(pairAddress) after creating the pair");
  console.log("3. Call enableTrading() when ready to launch");
  console.log("4. Verify contract on Basescan");
  console.log("──────────────────────────────────────────────────");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
