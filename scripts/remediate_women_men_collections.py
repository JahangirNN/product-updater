import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

def check_and_update_collection(handle, title, gender_tag):
    print(f"\n==========================================")
    print(f"Processing collection: {handle} ({title})")
    print(f"==========================================")
    
    # 1. Query existing collection
    q_get = """
    query getCol($handle: String!) {
      collectionByHandle(handle: $handle) {
        id
        title
        handle
        ruleSet {
          appliedDisjunctively
          rules {
            column
            relation
            condition
          }
        }
        productsCount {
          count
        }
      }
    }
    """
    data, ext, err = execute_shopify_graphql(q_get, {"handle": handle})
    col = data.get("collectionByHandle") if data else None
    
    if col:
        cid = col["id"]
        count = col.get("productsCount", {}).get("count")
        rule_set = col.get("ruleSet")
        print(f"Found existing collection {handle}: ID={cid}, count={count}, rules={rule_set}")
        
        # Try updating ruleSet via collectionUpdate
        mutation_update = """
        mutation updateCol($input: CollectionInput!) {
          collectionUpdate(input: $input) {
            collection {
              id
              handle
              productsCount {
                count
              }
              ruleSet {
                appliedDisjunctively
                rules {
                  column
                  relation
                  condition
                }
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        update_input = {
            "id": cid,
            "ruleSet": {
                "appliedDisjunctively": True,
                "rules": [
                    {"column": "TAG", "relation": "EQUALS", "condition": gender_tag},
                    {"column": "TAG", "relation": "EQUALS", "condition": f"{gender_tag}'s"}
                ]
            }
        }
        
        data_up, ext_up, err_up = execute_shopify_graphql(mutation_update, {"input": update_input})
        user_errors = data_up.get("collectionUpdate", {}).get("userErrors", []) if data_up else []
        
        if not user_errors and data_up and data_up.get("collectionUpdate", {}).get("collection"):
            updated_col = data_up["collectionUpdate"]["collection"]
            print(f"Successfully updated ruleSet on {handle}!")
            print(f"Updated collection: {updated_col}")
            return True
        else:
            print(f"collectionUpdate failed or returned userErrors: {user_errors} | Error: {err_up}")
            print(f"Need to recreate collection {handle} as a Smart Collection...")
            
            # Delete manual collection
            q_del = """
            mutation deleteCol($input: CollectionDeleteInput!) {
              collectionDelete(input: $input) {
                deletedCollectionId
                userErrors {
                  field
                  message
                }
              }
            }
            """
            data_del, ext_del, err_del = execute_shopify_graphql(q_del, {"input": {"id": cid}})
            print(f"Delete result: {data_del}")
            
    # Create smart collection
    mutation_create = """
    mutation createCol($input: CollectionInput!) {
      collectionCreate(input: $input) {
        collection {
          id
          title
          handle
          productsCount {
            count
          }
          ruleSet {
            appliedDisjunctively
            rules {
              column
              relation
              condition
            }
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    desc_html = f"<p>Explore our complete {title.lower()} luxury collection featuring designer handbags, fine horology, and statement accessories.</p>"
    
    create_input = {
        "title": title,
        "handle": handle,
        "descriptionHtml": desc_html,
        "ruleSet": {
            "appliedDisjunctively": True,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": gender_tag},
                {"column": "TAG", "relation": "EQUALS", "condition": f"{gender_tag}'s"}
            ]
        }
    }
    
    data_cr, ext_cr, err_cr = execute_shopify_graphql(mutation_create, {"input": create_input})
    res_cr = data_cr.get("collectionCreate", {}) if data_cr else {}
    errs = res_cr.get("userErrors", [])
    if not errs and res_cr.get("collection"):
        new_col = res_cr["collection"]
        print(f"SUCCESS: Created automated Smart Collection {handle} (ID: {new_col.get('id')})")
        print(f"Rules: {new_col.get('ruleSet')}")
        return True
    else:
        print(f"FAILED to create collection {handle}: {errs} | Error: {err_cr}")
        return False

if __name__ == "__main__":
    check_and_update_collection("women", "Women's Collection", "Women")
    check_and_update_collection("men", "Men's Collection", "Men")
