/**
 * Modern Multi-Select Dropdown Component
 * Provides a modern, accessible multi-select dropdown with search and grouping
 */

class ModernMultiSelect {
  constructor(element, options = {}) {
    this.element = element;
    this.originalSelect = element; // Store reference to original select element
    this.options = {
      placeholder: "Select options...",
      searchable: true,
      searchPlaceholder: "Search...",
      selectAll: false,
      groupBy: null,
      onSelect: null,
      onDeselect: null,
      onSelectAll: null,
      onDeselectAll: null,
      ...options,
    };

    this.selectedValues = new Set();
    this.filteredOptions = [];
    this.isOpen = false;

    this.init();
  }

  init() {
    this.createDropdown();
    this.bindEvents();
    this.updateDisplay();
  }

  createDropdown() {
    // Hide the original select element
    this.originalSelect.style.display = "none";

    // Create dropdown structure
    this.element.innerHTML = `
            <div class="modern-multiselect">
                <div class="dropdown-toggle" tabindex="0">
                    <span class="selected-text">${
                      this.options.placeholder
                    }</span>
                    <span class="selected-count" style="display: none;">0</span>
                    <span class="dropdown-arrow">▼</span>
                </div>
                <div class="dropdown-menu">
                    ${
                      this.options.searchable
                        ? `
                        <div class="search-box">
                            <input type="text" placeholder="${this.options.searchPlaceholder}" class="search-input">
                        </div>
                    `
                        : ""
                    }
                    ${
                      this.options.selectAll
                        ? `
                        <div class="select-all">
                            <input type="checkbox" class="select-all-checkbox">
                            <span>Select All</span>
                        </div>
                    `
                        : ""
                    }
                    <div class="dropdown-options"></div>
                </div>
            </div>
        `;

    this.dropdownToggle = this.element.querySelector(".dropdown-toggle");
    this.dropdownMenu = this.element.querySelector(".dropdown-menu");
    this.selectedText = this.element.querySelector(".selected-text");
    this.selectedCount = this.element.querySelector(".selected-count");
    this.searchInput = this.element.querySelector(".search-input");
    this.selectAllCheckbox = this.element.querySelector(".select-all-checkbox");
    this.dropdownOptions = this.element.querySelector(".dropdown-options");

    this.populateOptions();
  }

  populateOptions() {
    const options = this.getOptions();
    this.filteredOptions = [...options];
    this.renderOptions();
  }

  getOptions() {
    // The original select element is stored in this.originalSelect
    const selectElement =
      this.originalSelect || this.element.querySelector("select");
    if (!selectElement) return [];

    const options = [];
    const optgroups = selectElement.querySelectorAll("optgroup");

    if (optgroups.length > 0) {
      // Grouped options
      optgroups.forEach((optgroup) => {
        const groupLabel = optgroup.label;
        const groupOptions = Array.from(
          optgroup.querySelectorAll("option")
        ).map((option) => ({
          value: option.value,
          text: option.textContent,
          group: groupLabel,
          disabled: option.disabled,
          element: option,
        }));
        options.push(...groupOptions);
      });
    } else {
      // Regular options
      Array.from(selectElement.querySelectorAll("option")).forEach((option) => {
        options.push({
          value: option.value,
          text: option.textContent,
          group: null,
          disabled: option.disabled,
          element: option,
        });
      });
    }

    return options;
  }

  renderOptions() {
    // Refresh options from the original select element
    const options = this.getOptions();
    this.filteredOptions = [...options];

    if (this.filteredOptions.length === 0) {
      this.dropdownOptions.innerHTML =
        '<div class="no-options">No options found</div>';
      return;
    }

    // Check if "all" is selected
    const hasAllSelected = this.selectedValues.has("all");

    // Group options if needed
    const groupedOptions = this.groupOptions(this.filteredOptions);

    let html = "";
    Object.keys(groupedOptions).forEach((groupName) => {
      // Skip empty group labels if no options are available for this group
      const groupOptions = groupedOptions[groupName];
      if (groupOptions.length === 0) return;

      if (groupName !== "null") {
        html += `<div class="option-group">
                    <div class="option-group-label">${groupName}</div>
                `;
      }

      groupOptions.forEach((option) => {
        const isSelected = this.selectedValues.has(option.value);
        const isDisabled = hasAllSelected && option.value !== "all";

        html += `
                    <div class="option ${isSelected ? "selected" : ""} ${
          isDisabled ? "disabled" : ""
        }" data-value="${option.value}">
                        <input type="checkbox" ${isSelected ? "checked" : ""} ${
          option.disabled || isDisabled ? "disabled" : ""
        }>
                        <span class="option-text">${option.text}</span>
                    </div>
                `;
      });

      if (groupName !== "null") {
        html += "</div>";
      }
    });

    this.dropdownOptions.innerHTML = html;
    this.updateSelectAllState();
  }

  groupOptions(options) {
    const groups = {};
    options.forEach((option) => {
      const groupName = option.group || "null";
      // Only include options that are visible (not hidden by cascading logic)
      if (option.element && option.element.style.display !== "none") {
        if (!groups[groupName]) {
          groups[groupName] = [];
        }
        groups[groupName].push(option);
      }
    });
    return groups;
  }

  bindEvents() {
    // Toggle dropdown
    this.dropdownToggle.addEventListener("click", (e) => {
      e.preventDefault();
      this.toggle();
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", (e) => {
      if (!this.element.contains(e.target)) {
        this.close();
      }
    });

    // Search functionality
    if (this.searchInput) {
      this.searchInput.addEventListener("input", (e) => {
        this.filterOptions(e.target.value);
      });
    }

    // Option selection
    this.dropdownOptions.addEventListener("change", (e) => {
      if (e.target.type === "checkbox") {
        const option = e.target.closest(".option");
        const value = option.dataset.value;

        if (e.target.checked) {
          this.selectOption(value);
        } else {
          this.deselectOption(value);
        }
      }
    });

    // Select all functionality
    if (this.selectAllCheckbox) {
      this.selectAllCheckbox.addEventListener("change", (e) => {
        if (e.target.checked) {
          this.selectAll();
        } else {
          this.deselectAll();
        }
      });
    }

    // Keyboard navigation
    this.dropdownToggle.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        this.toggle();
      } else if (e.key === "Escape") {
        this.close();
      }
    });
  }

  filterOptions(searchTerm) {
    const term = searchTerm.toLowerCase();
    this.filteredOptions = this.getOptions().filter((option) =>
      option.text.toLowerCase().includes(term)
    );
    this.renderOptions();
  }

  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  open() {
    this.isOpen = true;
    this.dropdownToggle.classList.add("open");
    this.dropdownMenu.classList.add("show");

    // Focus search input if available
    if (this.searchInput) {
      setTimeout(() => this.searchInput.focus(), 100);
    }
  }

  close() {
    this.isOpen = false;
    this.dropdownToggle.classList.remove("open");
    this.dropdownMenu.classList.remove("show");
  }

  selectOption(value) {
    if (value === "all") {
      // If "all" is selected, clear all other selections
      this.selectedValues.clear();
      this.selectedValues.add("all");
    } else {
      // If any other option is selected, remove "all" if it exists
      this.selectedValues.delete("all");
      this.selectedValues.add(value);
    }

    this.updateDisplay();
    this.updateSelectAllState();
    this.renderOptions(); // Re-render to update disabled states

    if (this.options.onSelect) {
      this.options.onSelect(value);
    }
  }

  deselectOption(value) {
    this.selectedValues.delete(value);
    this.updateDisplay();
    this.updateSelectAllState();
    this.renderOptions(); // Re-render to update disabled states

    if (this.options.onDeselect) {
      this.options.onDeselect(value);
    }
  }

  selectAll() {
    const availableOptions = this.filteredOptions.filter(
      (option) => !option.disabled
    );
    availableOptions.forEach((option) => {
      this.selectedValues.add(option.value);
    });
    this.updateDisplay();
    this.renderOptions();

    if (this.options.onSelectAll) {
      this.options.onSelectAll();
    }
  }

  deselectAll() {
    this.selectedValues.clear();
    this.updateDisplay();
    this.renderOptions();

    if (this.options.onDeselectAll) {
      this.options.onDeselectAll();
    }
  }

  updateSelectAllState() {
    if (!this.selectAllCheckbox) return;

    const availableOptions = this.filteredOptions.filter(
      (option) => !option.disabled
    );
    const selectedCount = availableOptions.filter((option) =>
      this.selectedValues.has(option.value)
    ).length;

    if (selectedCount === 0) {
      this.selectAllCheckbox.indeterminate = false;
      this.selectAllCheckbox.checked = false;
    } else if (selectedCount === availableOptions.length) {
      this.selectAllCheckbox.indeterminate = false;
      this.selectAllCheckbox.checked = true;
    } else {
      this.selectAllCheckbox.indeterminate = true;
      this.selectAllCheckbox.checked = false;
    }
  }

  updateDisplay() {
    const count = this.selectedValues.size;

    if (count === 0) {
      this.selectedText.textContent = this.options.placeholder;
      this.selectedCount.style.display = "none";
    } else if (count === 1) {
      const selectedOption = this.getOptions().find((option) =>
        this.selectedValues.has(option.value)
      );
      this.selectedText.textContent = selectedOption
        ? selectedOption.text
        : this.options.placeholder;
      this.selectedCount.style.display = "none";
    } else {
      this.selectedText.textContent = `${count} items selected`;
      this.selectedCount.textContent = count;
      this.selectedCount.style.display = "inline-block";
    }
  }

  // Public methods
  getSelectedValues() {
    return Array.from(this.selectedValues);
  }

  setSelectedValues(values) {
    this.selectedValues.clear();
    values.forEach((value) => this.selectedValues.add(value));
    this.updateDisplay();
    this.renderOptions();
  }

  clear() {
    this.selectedValues.clear();
    this.updateDisplay();
    this.renderOptions();
  }

  destroy() {
    // Restore the original select element
    if (this.originalSelect) {
      this.originalSelect.style.display = "block";
    }
    // Clean up event listeners and DOM
    this.element.innerHTML = "";
  }
}

// Auto-initialize dropdowns
document.addEventListener("DOMContentLoaded", function () {
  // Initialize all select elements with data-modern-multiselect attribute
  document
    .querySelectorAll("select[data-modern-multiselect]")
    .forEach((select) => {
      const container = document.createElement("div");
      select.parentNode.insertBefore(container, select);
      select.style.display = "none";

      const options = {
        placeholder: select.dataset.placeholder || "Select options...",
        searchable: select.dataset.searchable !== "false",
        selectAll: select.dataset.selectAll === "true",
        onSelect: (value) => {
          // Update original select
          const option = select.querySelector(`option[value="${value}"]`);
          if (option) option.selected = true;

          // Trigger change event
          select.dispatchEvent(new Event("change", { bubbles: true }));
        },
        onDeselect: (value) => {
          // Update original select
          const option = select.querySelector(`option[value="${value}"]`);
          if (option) option.selected = false;

          // Trigger change event
          select.dispatchEvent(new Event("change", { bubbles: true }));
        },
      };

      new ModernMultiSelect(container, options);
    });
});

// Export for manual initialization
window.ModernMultiSelect = ModernMultiSelect;
