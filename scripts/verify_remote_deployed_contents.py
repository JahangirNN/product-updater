import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"
FILES_TO_CHECK = [
    "sections/hero-video.liquid",
    "snippets/product-card.liquid",
    "snippets/product-card-variants.liquid",
    "snippets/sneaker-vault-card.liquid",
    "snippets/variant-main-picker.liquid",
    "blocks/variant-picker.liquid",
    "templates/product.json",
    "snippets/luxury_sidebar_navigation.liquid",
    "snippets/header-drawer.liquid",
    "snippets/luxury-desktop-nav.liquid"
]

QUERY = """
query GetThemeFiles($themeId: ID!, $filenames: [String!]!) {
  theme(id: $themeId) {
    files(filenames: $filenames) {
      nodes {
        filename
        size
        updatedAt
        body {
          ... on OnlineStoreThemeFileBodyText {
            content
          }
        }
      }
    }
  }
}
"""

def main():
    res, _, err = execute_shopify_graphql(QUERY, variables={"themeId": THEME_ID, "filenames": FILES_TO_CHECK})
    nodes = res.get("theme", {}).get("files", {}).get("nodes", [])

    print(f"Fetched {len(nodes)} remote files from Shopify GraphQL:")
    for n in nodes:
        fn = n["filename"]
        sz = n["size"]
        up = n["updatedAt"]
        content = n.get("body", {}).get("content", "") if n.get("body") else ""
        print(f"  - {fn}: {sz} bytes (Updated: {up})")
        
        # Specific assertions
        if fn == "sections/hero-video.liquid":
            assert "hero-video-sound-btn" in content, "hero-video-sound-btn missing in remote!"
            assert "hero-video__sound-toggle" in content, "hero-video__sound-toggle missing in remote!"
            assert "hero-video__sound-icon--muted" in content, "muted icon missing in remote!"
            assert "hero-video__sound-icon--unmuted" in content, "unmuted icon missing in remote!"
        elif fn == "snippets/product-card-variants.liquid":
            assert "luxury-card__color-btn" in content, "luxury-card__color-btn missing in remote!"
            assert "luxury-card__size-pill" in content, "luxury-card__size-pill missing in remote!"
        elif fn == "snippets/product-card.liquid":
            assert "product-card-variants" in content, "product-card-variants missing in remote!"
            assert "swapCardImage" in content, "swapCardImage missing in remote!"
            assert "luxury-card__color-btn" in content, "luxury-card__color-btn styling missing in remote!"
        elif fn == "snippets/variant-main-picker.liquid":
            assert "swatch--variant-image" in content, "swatch--variant-image missing in remote!"
            assert "variant-option--pdp-single" in content, "variant-option--pdp-single missing in remote!"
            assert "variant-option__single-pill" in content, "variant-option__single-pill missing in remote!"
        elif fn == "blocks/variant-picker.liquid":
            assert "variant-main-picker" in content, "variant-main-picker missing in remote!"
        elif fn == "templates/product.json":
            assert "show_swatches" in content, "show_swatches missing in remote!"
        elif fn == "snippets/luxury_sidebar_navigation.liquid":
            assert "initSidebarAccordion" in content, "initSidebarAccordion missing in remote!"
            assert "dept-item.is-open" in content, "dept-item.is-open missing in remote!"
        elif fn == "snippets/header-drawer.liquid":
            assert "luxury-drawer-quick-btn" in content, "luxury-drawer-quick-btn missing in remote!"
            assert "luxury_sidebar_navigation" in content, "luxury_sidebar_navigation missing in remote!"
        elif fn == "snippets/luxury-desktop-nav.liquid":
            assert "0.8125rem" in content, "0.8125rem font size missing in remote!"
    print("\n[SUCCESS] ALL REMOTE THEME FILE ASSERTIONS CONFIRMED LIVE ON SHOPIFY THEME!")

if __name__ == "__main__":
    main()
