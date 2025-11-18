import React, { useState } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import { Navbar as MTNavbar, Typography, Button } from "@material-tailwind/react";

export function Navbar({ brandName, action }) {
  const [showLogin, setShowLogin] = useState(true);

  const handleLoginClick = () => {
    setShowLogin(false);
  };

  return (
    <MTNavbar color="transparent" className="p-3">
      <div className="container mx-auto flex items-center justify-between text-white">
        <Link to="/">
          <Typography className="cursor-pointer py-1.5 font-bold">
            {brandName}
          </Typography>
        </Link>

        {/* Only show login button if showLogin is true */}
        {showLogin &&
          React.cloneElement(action, {
            className: "inline-block",
            onClick: handleLoginClick,
          })}
      </div>
    </MTNavbar>
  );
}

Navbar.defaultProps = {
  brandName: "Baashha X",
  action: (
    <Link to="/login-selection">
      <Button variant="gradient" size="sm">
        Login
      </Button>
    </Link>
  ),
};

Navbar.propTypes = {
  brandName: PropTypes.string,
  action: PropTypes.node,
};

export default Navbar;
