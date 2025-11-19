from flask import Blueprint, jsonify, current_app
from global_utils.helpers.apiargs import from_body, from_query
from webargs import fields
from sharing.models import ShareItemKind, ShareStatus
from config.app_config import AppConfig

shares_bp = Blueprint("shares", __name__)


@shares_bp.route("/share.create", methods=["POST"])
@from_body({
    "recipient_user_id": fields.Str(data_key="recipientUserId", required=True),
    "item_kind": fields.Str(data_key="itemKind", required=True),
    "item_id": fields.Str(data_key="itemId", required=True),
    "message": fields.Str(required=False),
    "sender_user_id": fields.Str(data_key="senderUserId", required=False, load_default="alice")
})
def create_share(recipient_user_id, item_kind, item_id, message=None, sender_user_id="alice"):
    """Create share invitation."""
    try:
        # Validate item_kind
        try:
            kind = ShareItemKind(item_kind)
        except ValueError:
            return jsonify({"error": "Invalid itemKind. Must be 'resource' or 'blueprint'"}), 400

        svc = current_app.container.share_service
        share_id = svc.create_invite(
            sender_user_id=sender_user_id,
            recipient_user_id=recipient_user_id,
            item_kind=kind,
            item_id=item_id,
            message=message
        )

        return jsonify({
            "status": "success",
            "share_id": share_id
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@shares_bp.route("/share.accept", methods=["POST"])
@from_body({
    "share_id": fields.Str(data_key="shareId", required=True),
    "recipient_user_id": fields.Str(data_key="recipientUserId", required=False, load_default="alice")
})
def accept_share(share_id, recipient_user_id="alice"):
    """Accept share invitation."""
    try:
        svc = current_app.container.share_service
        result = svc.accept_invite(share_id, recipient_user_id=recipient_user_id)

        return jsonify({
            "status": "success",
            "result": result.model_dump(mode="json")
        }), 200

    except KeyError:
        return jsonify({"error": "Share invitation not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@shares_bp.route("/share.decline", methods=["POST"])
@from_body({
    "share_id": fields.Str(data_key="shareId", required=True),
    "recipient_user_id": fields.Str(data_key="recipientUserId", required=False, load_default="alice")
})
def decline_share(share_id, recipient_user_id="alice"):
    """Decline share invitation."""
    try:
        svc = current_app.container.share_service
        svc.decline_invite(share_id, recipient_user_id=recipient_user_id)

        return jsonify({"status": "success"}), 200

    except KeyError:
        return jsonify({"error": "Share invitation not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@shares_bp.route("/share.cancel", methods=["POST"])
@from_body({
    "share_id": fields.Str(data_key="shareId", required=True),
    "sender_user_id": fields.Str(data_key="senderUserId", required=False, load_default="alice")
})
def cancel_share(share_id, sender_user_id="alice"):
    """Cancel share invitation."""
    try:
        svc = current_app.container.share_service
        svc.cancel_invite(share_id, sender_user_id=sender_user_id)

        return jsonify({"status": "success"}), 200

    except KeyError:
        return jsonify({"error": "Share invitation not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@shares_bp.route("/shares.list", methods=["GET"])
@from_query({
    "direction": fields.Str(required=False, load_default="received"),
    "status": fields.Str(required=False),
    "skip": fields.Int(required=False, load_default=0),
    "limit": fields.Int(required=False, load_default=100),
    "user_id": fields.Str(data_key="userId", required=False, load_default="alice")
})
def list_shares(direction="received", status=None, skip=0, limit=100, user_id="alice"):
    """List share invitations."""
    try:
        # Validate status if provided
        status_enum = None
        if status:
            try:
                status_enum = ShareStatus(status)
            except ValueError:
                return jsonify({"error": "Invalid status"}), 400

        svc = current_app.container.share_service

        if direction == "received":
            invites = svc.list_received_invites(user_id, status_enum, skip, limit)
        elif direction == "sent":
            invites = svc.list_sent_invites(user_id, status_enum, skip, limit)
        else:
            return jsonify({"error": "Direction must be 'received' or 'sent'"}), 400

        return jsonify({
            "invites": [invite.model_dump(mode="json") for invite in invites],
            "count": len(invites)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@shares_bp.route("/share.get", methods=["GET"])
@from_query({
    "share_id": fields.Str(data_key="shareId", required=True),
    "user_id": fields.Str(data_key="userId", required=False, load_default="alice")
})
def get_share(share_id, user_id="alice"):
    """Get share invitation details."""
    try:
        svc = current_app.container.share_service
        invite = svc.get_invite(share_id)

        # Check authorization
        if invite.sender_user_id != user_id and invite.recipient_user_id != user_id:
            return jsonify({"error": "Not authorized to view this invitation"}), 403

        return jsonify(invite.model_dump(mode="json")), 200

    except KeyError:
        return jsonify({"error": "Share invitation not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== Public Chat Sharing Endpoints ==========

@shares_bp.route("/public-chat.enable", methods=["POST"])
@from_body({
    "blueprint_id": fields.Str(data_key="blueprintId", required=True),
    "user_id": fields.Str(data_key="userId", required=True),
})
def enable_public_chat(blueprint_id, user_id):
    """Enable public chat sharing for a blueprint."""
    try:
        bp_service = current_app.container.blueprint_service
        bp_service.enable_public_chat(blueprint_id, user_id)
        
        # Generate the share link (using blueprint_id as token)
        config = AppConfig.get_instance()
        frontend_url = config.get('frontend_url', 'http://localhost:5000')
        share_link = f"{frontend_url}/chat/{blueprint_id}"
        
        return jsonify({
            "status": "success",
            "enabled": True,
            "share_link": share_link,
            "blueprint_id": blueprint_id
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except KeyError as e:
        return jsonify({"error": f"Blueprint not found: {blueprint_id}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@shares_bp.route("/public-chat.disable", methods=["POST"])
@from_body({
    "blueprint_id": fields.Str(data_key="blueprintId", required=True),
    "user_id": fields.Str(data_key="userId", required=True),
})
def disable_public_chat(blueprint_id, user_id):
    """Disable public chat sharing for a blueprint."""
    try:
        bp_service = current_app.container.blueprint_service
        bp_service.disable_public_chat(blueprint_id, user_id)
        
        return jsonify({
            "status": "success",
            "enabled": False
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except KeyError as e:
        return jsonify({"error": f"Blueprint not found: {blueprint_id}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@shares_bp.route("/public-chat.status.get", methods=["GET"])
@from_query({
    "blueprint_id": fields.Str(data_key="blueprintId", required=True),
})
def get_public_chat_status(blueprint_id):
    """Get public chat sharing status for a blueprint."""
    try:
        bp_service = current_app.container.blueprint_service
        enabled = bp_service.is_public_chat_enabled(blueprint_id)
        
        # Generate the share link if enabled
        config = AppConfig.get_instance()
        frontend_url = config.get('frontend_url', 'http://localhost:5000')
        share_link = f"{frontend_url}/chat/{blueprint_id}" if enabled else None
        
        return jsonify({
            "enabled": enabled,
            "share_link": share_link,
            "blueprint_id": blueprint_id
        }), 200
    except KeyError as e:
        return jsonify({
            "enabled": False,
            "share_link": None
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@shares_bp.route("/public-chat.validate", methods=["GET"])
@from_query({
    "blueprint_id": fields.Str(data_key="blueprintId", required=True),
})
def validate_public_chat_token(blueprint_id):
    """Validate a public chat token (blueprint_id) and return blueprint info if valid."""
    try:
        bp_service = current_app.container.blueprint_service
        
        # Check if blueprint exists and public chat is enabled
        if not bp_service.exists(blueprint_id):
            return jsonify({
                "valid": False,
                "error": "Blueprint not found"
            }), 404
        
        if not bp_service.is_public_chat_enabled(blueprint_id):
            return jsonify({
                "valid": False,
                "error": "Public chat sharing is disabled for this blueprint"
            }), 404
        
        # Get blueprint info
        bp_doc = bp_service.get_blueprint_draft_doc(blueprint_id)
        bp_name = bp_doc.get("spec_dict", {}).get("name", "Unnamed Workflow")
        
        return jsonify({
            "valid": True,
            "blueprint_id": blueprint_id,
            "blueprint_name": bp_name
        }), 200
    except KeyError as e:
        return jsonify({
            "valid": False,
            "error": "Blueprint not found"
        }), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
