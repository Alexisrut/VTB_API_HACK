import { createContext, useContext, type ReactNode } from "react";
import { Loader } from "../components/Loader";
import type { UserResponse } from "../utils/api";
import { useAuth } from "./useAuth";

export type AppContext = {
    me: UserResponse | null;
}

const AppReactContext = createContext<AppContext>({
    me: null,
});


export const useAppContext = () => {
  return useContext(AppReactContext);
};

export const useMe = () => {
  const { me } = useAppContext();
  return me; 
};

export const AppContextProvider = ({
    children,
}: {
    children: ReactNode;
}) => {
    const { user, isLoading, error} = useAuth();
    return (
    <AppReactContext.Provider
      value={{
        me: user || null,
      }}
    >
      {isLoading ? (
        <Loader/>
      ) : error ? (
        <p>Error: {error}</p>
      ) : (
        children
      )}
    </AppReactContext.Provider>
  );
};