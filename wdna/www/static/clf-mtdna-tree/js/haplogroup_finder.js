/**
 * Haplogroup finder module
 * This module provides functionality to find haplogroup based on mutations
 */

// Helper functions for mutation parsing and validation
function parseMutations(mutationsString) {
    if (!mutationsString) return [];
    return mutationsString.split(',')
        .map(m => m.trim())
        .filter(m => m.length > 0);
}

function validateMutations(mutations) {
    const valid = [];
    const invalid = [];
    
    for (const mutation of mutations) {
        // Basic mutation format validation
        // Accepts: numbers (e.g., 6065), numbers with letters (e.g., 10533T),
        // and special formats like 2679.1G or 9914.1GT
        if (/^\d+(\.\d+)?[A-Z]*$/.test(mutation)) {
            valid.push(mutation);
        } else {
            invalid.push(mutation);
        }
    }
    
    return { valid, invalid };
}

class HaplogroupFinder {
    constructor(treeData) {
        this.treeData = treeData;
    }

    /**
     * Check if mutations match with haplogroup modifications
     * @param {Array} mutations - Array of mutations to check
     * @param {Array} modifications - Array of haplogroup modifications
     * @returns {boolean} - True if mutations match modifications
     */
    checkModifications(mutations, modifications) {
        if (!modifications || !mutations) {
            return false;
        }

        // Convert both arrays to sets for easier comparison
        const mutationSet = new Set(mutations.map(m => m.toString()));
        const modificationSet = new Set(modifications.map(m => m.toString()));

        // Count how many modifications match
        let matchCount = 0;
        for (const mod of modificationSet) {
            if (mutationSet.has(mod)) {
                matchCount++;
            }
        }

        // Return true if at least one modification matches
        return matchCount > 0;
    }

    /**
     * Find haplogroup by traversing the tree
     * @param {Object} node - Current tree node
     * @param {Array} mutations - Array of mutations to check
     * @returns {Object} - Found haplogroup info or null
     */
    findHaplogroupInNode(node, mutations) {
        if (!node) {
            console.log("Node is null");
            return null;
        }

        console.log("Starting search from node:", node.name);
        console.log("Initial mutations:", mutations);

        let currentNode = node;
        let remainingMutations = new Set(mutations.map(m => m.toString()));
        let pathFromReference = []; // Path from reference sample

        // Check current node and go up until we find a node whose mutations don't match our set
        while (currentNode && currentNode.parent !== "null") {
            console.log("Checking node:", currentNode.name, "with mods:", currentNode.mods);
            pathFromReference.push(currentNode.name);

            // Check if all mutations of current node are in our set
            let hasAllCurrentNodeMods = true;
            if (currentNode.mods) {
                for (const mod of currentNode.mods) {
                    if (!remainingMutations.has(mod.toString())) {
                        hasAllCurrentNodeMods = false;
                        break;
                    }
                }
            }

            // If we don't have all mutations of current node
            if (!hasAllCurrentNodeMods) {
                console.log("Node", currentNode.name, "has mutations that don't match our set");
                // Check children of current node (but not those from our path)
                if (currentNode.children) {
                    for (const child of currentNode.children) {
                        // Skip children that are on the path from reference sample
                        if (pathFromReference.includes(child.name)) {
                            console.log("Skipping child", child.name, "as it's on reference path");
                            continue;
                        }
                        
                        if (!child.mods) continue;
                        
                        for (const mod of child.mods) {
                            if (remainingMutations.has(mod.toString())) {
                                console.log("Found matching mutation", mod, "in child", child.name);
                                return {
                                    name: child.name,
                                    parent: child.parent,
                                    modifications: child.mods
                                };
                            }
                        }
                    }
                }
                // If we didn't find matching child, return parent of current node
                console.log("No matching children found, returning parent of current node:", currentNode.parent);
                const parentNode = this.findParentNode(currentNode.parent);
                return {
                    name: currentNode.parent,
                    parent: parentNode?.parent || null,
                    modifications: parentNode?.mods || []
                };
            }

            // If we have all mutations, remove them from remaining and go to parent
            if (currentNode.mods) {
                for (const mod of currentNode.mods) {
                    remainingMutations.delete(mod.toString());
                }
            }

            console.log("Remaining mutations after", currentNode.name, ":", Array.from(remainingMutations));

            // Check if remaining mutations have anything that matches the next node
            const parentNode = this.findParentNode(currentNode.parent);
            if (parentNode && parentNode.mods) {
                let hasMatchingParentMod = false;
                for (const mod of parentNode.mods) {
                    if (remainingMutations.has(mod.toString())) {
                        hasMatchingParentMod = true;
                        break;
                    }
                }
                if (!hasMatchingParentMod) {
                    console.log("Parent has no matching mutations, checking children of parent:", parentNode.name);
                    // Check children of parent (but not those from our path)
                    if (parentNode.children) {
                        for (const child of parentNode.children) {
                            // Skip children that are on the path from reference sample
                            if (pathFromReference.includes(child.name)) {
                                console.log("Skipping child", child.name, "as it's on reference path");
                                continue;
                            }
                            
                            if (!child.mods) continue;
                            
                            for (const mod of child.mods) {
                                if (remainingMutations.has(mod.toString())) {
                                    console.log("Found matching mutation", mod, "in child", child.name);
                                    return {
                                        name: child.name,
                                        parent: child.parent,
                                        modifications: child.mods
                                    };
                                }
                            }
                        }
                    }
                    
                    console.log("No matching children found, returning parent:", parentNode.name);
                    return {
                        name: parentNode.name,
                        parent: parentNode?.parent || null,
                        modifications: parentNode?.mods || []
                    };
                }
            }

            currentNode = parentNode;
        }

        console.log("No matches found");
        return null;
    }

    /**
     * Find parent node by name
     * @param {string} parentName - Name of the parent node to find
     * @returns {Object} - Parent node or null
     */
    findParentNode(parentName) {
        const findNode = (node) => {
            if (!node) return null;
            
            if (node.name === parentName) {
                return node;
            }
            
            if (node.children) {
                for (const child of node.children) {
                    const found = findNode(child);
                    if (found) {
                        return found;
                    }
                }
            }
            return null;
        };

        return findNode(this.treeData);
    }

    /**
     * Find haplogroup based on mutations
     * @param {Array} mutations - Array of mutations to check
     * @param {string} startHaplogroup - Starting haplogroup name
     * @returns {Object} - Found haplogroup info or null
     */
    findHaplogroup(mutations, startHaplogroup = "A1a1a1a1a*") {
        // Validate input
        if (!Array.isArray(mutations) || mutations.length === 0) {
            throw new Error("Mutations must be a non-empty array");
        }

        console.log("Starting search with mutations:", mutations);

        // First check if we have the reference mutations
        const refMutations = new Set(["2679.1G", "6065", "8368", "9914.1GT"].map(m => m.toString()));
        const inputMutations = new Set(mutations.map(m => m.toString()));
        
        let hasAllRefMutations = true;
        for (const refMut of refMutations) {
            if (!inputMutations.has(refMut)) {
                hasAllRefMutations = false;
                break;
            }
        }

        if (!hasAllRefMutations) {
            console.log("Missing reference mutations");
            return null;
        }

        // Find starting node
        const startNode = this.findParentNode(startHaplogroup);
        if (!startNode) {
            throw new Error(`Starting haplogroup ${startHaplogroup} not found`);
        }

        console.log("Found start node:", startNode.name);

        // First check if we need to go to parent
        if (startNode.mods) {
            let hasAllStartNodeMods = true;
            for (const mod of startNode.mods) {
                if (!inputMutations.has(mod.toString())) {
                    hasAllStartNodeMods = false;
                    break;
                }
            }
            
            if (!hasAllStartNodeMods) {
                console.log("Start node mutations don't match, going to parent:", startNode.parent);
                const parentNode = this.findParentNode(startNode.parent);
                if (parentNode) {
                    return this.findHaplogroupInNode(parentNode, mutations);
                }
            }
        }

        // If we're still here, start search from the starting node
        return this.findHaplogroupInNode(startNode, mutations);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HaplogroupFinder;
} else {
    window.HaplogroupFinder = HaplogroupFinder;
}
