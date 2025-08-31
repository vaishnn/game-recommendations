document.addEventListener("DOMContentLoaded", () => {
  // --- DOM Elements ---
  const steamIdInput = document.getElementById("steamIdInput");
  const fetchGamesBtn = document.getElementById("fetchGamesBtn");
  const apiStatus = document.getElementById("api-status");
  const API_BASE_URL =
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname === "localhost"
      ? "http://127.0.0.1:4000"
      : "https://recommend.vaishnav3d.org";

  const gameLibrarySection = document.getElementById("game-library-section");
  const gameSearchInput = document.getElementById("gameSearchInput");
  const gameList = document.getElementById("game-library-list");

  const rightPanel = document.getElementById("right-panel-main");
  const recommendButton = document.getElementById("recommend-button");
  const nicheSlider = document.getElementById("niche-slider");
  const nicheValueDisplay = document.getElementById("niche-value-display");

  // FIX: Corrected the element IDs for the output section and list
  const recommendationsSection = document.getElementById(
    "recommendations-output",
  );
  const recommendationList = document.getElementById("recommendations-list");

  // --- State ---
  let allGames = [];
  let selectedGames = new Map();

  // --- Event Listeners ---˝`
  fetchGamesBtn.addEventListener("click", handleFetchGames);
  gameSearchInput.addEventListener("input", handleSearch);
  gameList.addEventListener("click", handleGameSelectionToggle);
  recommendButton.addEventListener("click", handleGetRecommendations);
  nicheSlider.addEventListener("input", (e) => {
    nicheValueDisplay.textContent = parseFloat(e.target.value).toFixed(1);
  });

  // --- Main Functions ---

  /**
   * Fetches games for the provided SteamID by calling our Python backend.
   */
  async function handleFetchGames() {
    const steamId = steamIdInput.value.trim();
    if (!/^\d{17}$/.test(steamId)) {
      showStatus("Please enter a valid 17-digit SteamID64.", "error");
      return;
    }

    resetUI();
    showStatus("Fetching your game library...", "loading");
    fetchGamesBtn.disabled = true;
    fetchGamesBtn.querySelector("span").textContent = "Fetching...";

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/get-games?steamid=${steamId}`,
      );
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.error || `HTTP error! Status: ${response.status}`,
        );
      }
      const data = await response.json();

      if (data.games && data.games.length > 0) {
        showStatus(`Successfully fetched ${data.game_count} games!`, "success");
        allGames = data.games.sort((a, b) => a.name.localeCompare(b.name));
        renderGameList(allGames);
        gameLibrarySection.style.display = "block";
      } else {
        showStatus(
          "Could not find any games or the profile is private.",
          "error",
        );
      }
    } catch (error) {
      console.error("Error fetching Steam games:", error);
      showStatus(
        `Error: ${error.message}. Is the Python server running?`,
        "error",
      );
    } finally {
      fetchGamesBtn.disabled = false;
      fetchGamesBtn.querySelector("span").textContent = "Fetch Games";
    }
  }

  /**
   * Gathers settings, calls the ML model API, and renders the results.
   */
  async function handleGetRecommendations() {
    const inputGames = [];

    // FIX: Iterate over the reliable 'selectedGames' map instead of the DOM
    // This prevents bugs caused by the search filter.
    for (const appId of selectedGames.keys()) {
      let multiplier = 1.0; // Default multiplier
      let type = "like"; // Default type

      // Try to find the controls in the DOM to get current slider values
      const listItem = gameList.querySelector(`li[data-appid="${appId}"]`);
      const controls = listItem
        ? listItem.querySelector(".tuning-controls")
        : null;

      if (controls) {
        // If the item is visible and has controls, use its values
        multiplier =
          parseInt(controls.querySelector(".influence-slider").value, 10) / 100;
        type = controls.querySelector(".opposite-toggle").checked
          ? "opposite"
          : "like";
      }

      inputGames.push({
        id: parseInt(appId, 10),
        multiplier: multiplier,
        type: type,
      });
    }

    if (inputGames.length === 0) {
      showStatus(
        "Please select at least one game to get recommendations.",
        "error",
      );
      return;
    }

    const recommendationParams = {
      input_games: inputGames,
      niche_factor: parseFloat(nicheSlider.value),
    };

    showStatus("Getting recommendations from the model...", "loading");
    recommendButton.disabled = true;
    // FIX: Target the <span> to preserve the button's icon
    recommendButton.querySelector("span").textContent = "Thinking...";
    recommendationsSection.style.display = "none";

    try {
      const response = await fetch(`${API_BASE_URL}/api/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(recommendationParams),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.error || `HTTP error! Status: ${response.status}`,
        );
      }

      const recommendations = await response.json();
      showStatus("Here are your recommendations!", "success");
      renderRecommendations(recommendations);
    } catch (error) {
      console.error("Error fetching recommendations:", error);
      showStatus(`Error: ${error.message}`, "error");
    } finally {
      recommendButton.disabled = false;
      recommendButton.querySelector("span").textContent = "Get Recommendations";
    }
  }

  /**
   * Renders the list of recommended games.
   */
  function renderRecommendations(recommendations) {
    if (!recommendations || recommendations.length === 0) {
      recommendationList.innerHTML =
        "<li>Sorry, no recommendations could be generated with these selections.</li>";
    } else {
      recommendationList.innerHTML = recommendations
        .map(
          (game) => `
                <li class="recommendation-item">
                    <img class="game-icon" src="https://cdn.akamai.steamstatic.com/steam/apps/${game.id}/capsule_184x69.jpg" alt="${game.name} icon">
                    <div class="recommendation-details">
                        <div class="recommendation-name">${game.name}</div>
                        <div class="recommendation-desc">${game.short_description}</div>
                    </div>
                </li>
                `,
        )
        .join("");
    }
    recommendationsSection.style.display = "block";
  }

  /**
   * Filters the rendered game list based on the search input.
   */
  function handleSearch(event) {
    const query = event.target.value.toLowerCase();
    const filteredGames = allGames.filter((game) =>
      game.name.toLowerCase().includes(query),
    );
    renderGameList(filteredGames);
    // Re-apply selection styles and controls after re-rendering
    gameList.querySelectorAll("li").forEach((li) => {
      if (selectedGames.has(li.dataset.appid)) {
        li.classList.add("selected");
        addTuningControls(li);
      }
    });
  }

  /**
   * Toggles the selection state of a game in the list.
   */
  function handleGameSelectionToggle(event) {
    const li = event.target.closest("li");
    if (!li || !li.dataset.appid) return; // Ensure it's a valid game item
    if (event.target.closest(".tuning-controls")) return;

    const appId = li.dataset.appid;
    const gameName = li.dataset.name;

    if (selectedGames.has(appId)) {
      selectedGames.delete(appId);
      li.classList.remove("selected");
      removeTuningControls(li);
    } else {
      selectedGames.set(appId, { name: gameName });
      li.classList.add("selected");
      addTuningControls(li);
    }
    updateRightPanelVisibility();
  }

  /**
   * Renders the list of games into the DOM.
   */
  function renderGameList(games) {
    if (games.length === 0) {
      gameList.innerHTML = "<li>No games found matching your search.</li>";
      return;
    }
    gameList.innerHTML = games
      .map(
        (game) => `
            <li data-appid="${game.appid}" data-name="${game.name}">
                <div class="game-item-header">
                    <img class="game-icon" src="https://cdn.akamai.steamstatic.com/steam/apps/${game.appid}/capsule_184x69.jpg" alt="${game.name} icon">
                    <label>${game.name}</label>
                </div>
            </li>
            `,
      )
      .join("");
  }

  /**
   * Injects tuning controls into a selected game's list item.
   */
  function addTuningControls(listItem) {
    // Prevent adding controls if they already exist
    if (listItem.querySelector(".tuning-controls")) return;

    const controlsContainer = document.createElement("div");
    controlsContainer.className = "tuning-controls";
    controlsContainer.innerHTML = `
            <div class="influence-header">
                <label>Influence</label>
                <span class="influence-percentage">100%</span>
            </div>
            <div class="slider-container">
                <span class="slider-label">0%</span>
                <input type="range" class="influence-slider" min="0" max="200" value="100">
                <span class="slider-label">200%</span>
            </div>
            <div class="toggle-switch">
                <span>Recommend Similar</span>
                <label class="switch">
                    <input type="checkbox" class="opposite-toggle">
                    <span class="slider-toggle"></span>
                </label>
                <span>Opposite</span>
            </div>
        `;
    listItem.appendChild(controlsContainer);

    controlsContainer
      .querySelector(".influence-slider")
      .addEventListener("input", (e) => {
        controlsContainer.querySelector(".influence-percentage").textContent =
          `${e.target.value}%`;
      });
  }

  /**
   * Removes tuning controls from a deselected list item.
   */
  function removeTuningControls(listItem) {
    const controls = listItem.querySelector(".tuning-controls");
    if (controls) controls.remove();
  }

  /**
   * Shows or hides the right panel based on whether any games are selected.
   */
  function updateRightPanelVisibility() {
    rightPanel.style.display = selectedGames.size > 0 ? "flex" : "none";
  }

  /**
   * Displays a status message to the user.
   */
  function showStatus(message, type) {
    apiStatus.textContent = message;
    apiStatus.className = `status-message ${type}`;
    apiStatus.style.display = "block";
  }

  /**
   * Resets the UI when fetching a new library.
   */
  function resetUI() {
    gameLibrarySection.style.display = "none";
    rightPanel.style.display = "none";
    recommendationsSection.style.display = "none";
    gameList.innerHTML = "";
    allGames = [];
    selectedGames.clear();
    apiStatus.style.display = "none";
  }
});
